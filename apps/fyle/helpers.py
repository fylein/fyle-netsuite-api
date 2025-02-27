import json
import logging
import traceback
import requests
from datetime import datetime, timezone
from fyle_integrations_platform_connector import PlatformConnector

from django.conf import settings
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from fyle_accounting_mappings.models import ExpenseAttribute

from apps.fyle.models import ExpenseGroupSettings, ExpenseFilter, ExpenseGroup, Expense
from apps.tasks.models import TaskLog
from apps.workspaces.models import FyleCredential, Workspace, Configuration
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import FyleCredential, Workspace, Configuration
from typing import List, Union

import django_filters

logger = logging.getLogger(__name__)

SOURCE_ACCOUNT_MAP = {'PERSONAL': 'PERSONAL_CASH_ACCOUNT', 'CCC': 'PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT'}


def get_updated_accounting_export_summary(
        expense_id: str, state: str, error_type: Union[str, None], url: Union[str, None], is_synced: bool) -> dict:
    """
    Get updated accounting export summary
    :param expense_id: expense id
    :param state: state
    :param error_type: error type
    :param url: url
    :param is_synced: is synced
    :return: updated accounting export summary
    """
    return {
        'id': expense_id,
        'state': state,
        'error_type': error_type,
        'url': url,
        'synced': is_synced
    }

def get_batched_expenses(batched_payload: List[dict], workspace_id: int) -> List[Expense]:
    """
    Get batched expenses
    :param batched_payload: batched payload
    :param workspace_id: workspace id
    :return: batched expenses
    """
    expense_ids = [expense['id'] for expense in batched_payload]
    return Expense.objects.filter(expense_id__in=expense_ids, workspace_id=workspace_id)



def get_exportable_expense_group_ids(workspace_id):
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    fund_source = []

    if configuration.reimbursable_expenses_object:
        fund_source.append('PERSONAL')
    if configuration.corporate_credit_card_expenses_object:
        fund_source.append('CCC')

    expense_group_ids = ExpenseGroup.objects.filter(
        workspace_id=workspace_id,
        exported_at__isnull=True,
        fund_source__in=fund_source,
        expenses__is_skipped=False
    ).values_list('id', flat=True)
    
    return expense_group_ids


def post_request(url, body, refresh_token=None):
    """
    Create a HTTP post request.
    """
    access_token = None
    api_headers = {
        'Content-Type': 'application/json',
    }
    if refresh_token:
        access_token = get_access_token(refresh_token)

        api_headers['Authorization'] = 'Bearer {0}'.format(access_token)

    response = requests.post(
        url,
        headers=api_headers,
        data=json.dumps(body)
    )

    if response.status_code in [200, 201]:
        return json.loads(response.text)
    else:
        raise Exception(response.text)


def get_source_account_type(fund_source: List[str]) -> List[str]:
    """
    Get source account type
    :param fund_source: fund source
    :return: source account type
    """
    source_account_type = []
    for source in fund_source:
        source_account_type.append(SOURCE_ACCOUNT_MAP[source])

    return source_account_type


def get_filter_credit_expenses(expense_group_settings: ExpenseGroupSettings) -> bool:
    """
    Get filter credit expenses
    :param expense_group_settings: expense group settings
    :return: filter credit expenses
    """
    filter_credit_expenses = True
    if expense_group_settings.import_card_credits:
        filter_credit_expenses = False

    return filter_credit_expenses


def get_fund_source(workspace_id: int) -> List[str]:
    """
    Get fund source
    :param workspace_id: workspace id
    :return: fund source
    """
    general_settings = Configuration.objects.get(workspace_id=workspace_id)
    fund_source = []
    if general_settings.reimbursable_expenses_object:
        fund_source.append('PERSONAL')
    if general_settings.corporate_credit_card_expenses_object:
        fund_source.append('CCC')

    return fund_source


def handle_import_exception(task_log: TaskLog) -> None:
    """
    Handle import exception
    :param task_log: task log
    :return: None
    """
    error = traceback.format_exc()
    task_log.detail = {'error': error}
    task_log.status = 'FATAL'
    task_log.save()
    logger.error('Something unexpected happened workspace_id: %s %s', task_log.workspace_id, task_log.detail)


def get_request(url, params, refresh_token):
    """
    Create a HTTP get request.
    """
    access_token = get_access_token(refresh_token)
    api_headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {0}'.format(access_token)
    }
    api_params = {}

    for k in params:
        # ignore all unused params
        if not params[k] is None:
            p = params[k]

            # convert boolean to lowercase string
            if isinstance(p, bool):
                p = str(p).lower()

            api_params[k] = p

    response = requests.get(
        url,
        headers=api_headers,
        params=api_params
    )

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        raise Exception(response.text)


def get_access_token(refresh_token: str) -> str:
    """
    Get access token from fyle
    """
    api_data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': settings.FYLE_CLIENT_ID,
        'client_secret': settings.FYLE_CLIENT_SECRET
    }
    return post_request(settings.FYLE_TOKEN_URI, body=api_data)['access_token']


def get_fyle_orgs(refresh_token: str, cluster_domain: str):
    """
    Get fyle orgs of a user
    """
    api_url = '{0}/api/orgs/'.format(cluster_domain)

    return get_request(api_url, {}, refresh_token)


def get_cluster_domain(refresh_token: str) -> str:
    """
    Get cluster domain name from fyle
    :param refresh_token: (str)
    :return: cluster_domain (str)
    """
    cluster_api_url = '{0}/oauth/cluster/'.format(settings.FYLE_BASE_URL)

    return post_request(cluster_api_url, {}, refresh_token)['cluster_domain']

def add_expense_id_to_expense_group_settings(workspace_id: int):
    """
    Add Expense id to card expense grouping
    :param workspace_id: Workspace id
    return: None
    """
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    ccc_expense_group_fields = expense_group_settings.corporate_credit_card_expense_group_fields
    ccc_expense_group_fields.append('expense_id')
    ccc_expense_group_fields.append('spent_at')
    expense_group_settings.corporate_credit_card_expense_group_fields = list(set(ccc_expense_group_fields))
    expense_group_settings.ccc_export_date_type = 'spent_at'
    expense_group_settings.save()


def update_import_card_credits_flag(corporate_credit_card_expenses_object: str, reimbursable_expenses_object: str, workspace_id: int) -> None:
    """
    set import_card_credits flag to True in ExpenseGroupSettings
    :param corporate_credit_card_expenses_object: Corporate credit card expenses object
    :param workspace_id: Workspace id
    return: None
    """
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    import_card_credits = None

    if (corporate_credit_card_expenses_object == 'EXPENSE REPORT' or (reimbursable_expenses_object and reimbursable_expenses_object in ['EXPENSE REPORT', 'JOURNAL ENTRY'])) and not expense_group_settings.import_card_credits:
        import_card_credits = True
    elif (corporate_credit_card_expenses_object != 'EXPENSE REPORT' and (reimbursable_expenses_object and reimbursable_expenses_object not in ['EXPENSE REPORT', 'JOURNAL ENTRY'])) and expense_group_settings.import_card_credits:
        import_card_credits = False

    if corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE':
        import_card_credits = True

    if import_card_credits is not None and import_card_credits != expense_group_settings.import_card_credits:
        expense_group_settings.import_card_credits = import_card_credits
        expense_group_settings.save()


def update_use_employee_attributes_flag(workspace_id: int) -> None:
    """
    Update use_employee_department, use_employee_location, use_employee_class in GeneralMapping
    :param workspace_id: Workspace id
    return: None
    """
    general_mapping = GeneralMapping.objects.filter(workspace_id=workspace_id).first()
    if general_mapping:
        if general_mapping.use_employee_department:
            general_mapping.use_employee_department = False
            general_mapping.department_level = None

        if general_mapping.use_employee_location:
            general_mapping.use_employee_location = False

        if general_mapping.use_employee_class:
            general_mapping.use_employee_class = False

        general_mapping.save()


def check_interval_and_sync_dimension(workspace_id: int):
    """
    Check sync interval and sync dimension
    :param workspace_id: Workspace ID
    """

    workspace = Workspace.objects.get(pk=workspace_id)

    if workspace.source_synced_at:
        time_interval = datetime.now(timezone.utc) - workspace.source_synced_at

    if workspace.source_synced_at is None or time_interval.days > 0:
        sync_dimensions(workspace_id)



def sync_dimensions(workspace_id, is_export: bool = False) -> None:
    workspace = Workspace.objects.get(id=workspace_id)
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace.id)

    platform = PlatformConnector(fyle_credentials)
    platform.import_fyle_dimensions(is_export=is_export)
    if is_export:
        categories_count = platform.categories.get_count()

        categories_expense_attribute_count = ExpenseAttribute.objects.filter(
            attribute_type="CATEGORY", workspace_id=fyle_credentials.workspace_id, active=True
        ).count()

        if categories_count != categories_expense_attribute_count:
            platform.categories.sync()

        projects_count = platform.projects.get_count()

        projects_expense_attribute_count = ExpenseAttribute.objects.filter(
            attribute_type="PROJECT", workspace_id=fyle_credentials.workspace_id, active=True
        ).count()

        if projects_count != projects_expense_attribute_count:
            platform.projects.sync()

    workspace.source_synced_at = datetime.now()
    workspace.save(update_fields=['source_synced_at'])

def construct_expense_filter_query(expense_filters: list[ExpenseFilter]) -> Q:
    """
    Construct the expense filter query
    :param expense_filters: Expense filters
    :return: Constructed expense filter query
    """
    final_filter = None
    previous_join_by = None
    for expense_filter in expense_filters:
        constructed_expense_filter = construct_expense_filter(expense_filter)

        # If this is the first filter, set it as the final filter
        if expense_filter.rank == 1:
            final_filter = (constructed_expense_filter)

        # If join by is AND, OR
        elif expense_filter.rank != 1:
            if previous_join_by == 'AND':
                final_filter = final_filter & (constructed_expense_filter)
            elif previous_join_by == 'OR':
                final_filter = final_filter | (constructed_expense_filter)
            # If no join_by is specified, don't combine the filters

        # Set the join type for the additional filter
        previous_join_by = expense_filter.join_by

    return final_filter

def construct_expense_filter(expense_filter: ExpenseFilter) -> Q:
    """
    Construct the expense filter
    :param expense_filter: Expense filter
    :return: Constructed expense filter
    """
    # If the expense filter is a custom field
    if expense_filter.is_custom:
        # If the operator is not isnull
        if expense_filter.operator != 'isnull':
            # If the custom field is of type SELECT and the operator is not_in
            if expense_filter.custom_field_type == 'SELECT' and expense_filter.operator == 'not_in':
                # Construct the filter for the custom property
                filter1 = {
                    f'custom_properties__{expense_filter.condition}__in': expense_filter.values
                }
                # Invert the filter using the ~Q operator and assign it to the constructed expense filter
                constructed_expense_filter = ~Q(**filter1)
            else:
                # If the custom field is of type NUMBER, convert the values to integers
                if expense_filter.custom_field_type == 'NUMBER':
                    expense_filter.values = [int(value) for value in expense_filter.values]
                # If the expense filter is a custom field and the operator is yes or no(checkbox)
                if expense_filter.custom_field_type == 'BOOLEAN':
                    expense_filter.values[0] = True if expense_filter.values[0] == 'true' else False
                # Construct the filter for the custom property
                filter1 = {
                    f'custom_properties__{expense_filter.condition}__{expense_filter.operator}':
                        expense_filter.values[0] if len(expense_filter.values) == 1 and expense_filter.operator != 'in'
                        else expense_filter.values
                }
                # Assign the constructed filter to the constructed expense filter
                constructed_expense_filter = Q(**filter1)

        # If the expense filter is a custom field and the operator is isnull
        elif expense_filter.operator == 'isnull':
            # Determine the value for the isnull filter based on the first value in the values list
            expense_filter_value: bool = True if expense_filter.values[0].lower() == 'true' else False
            # Construct the isnull filter for the custom property
            filter1 = {
                f'custom_properties__{expense_filter.condition}__isnull': expense_filter_value
            }
            # Construct the exact filter for the custom property
            filter2 = {
                f'custom_properties__{expense_filter.condition}__exact': None
            }
            if expense_filter_value:
                # If the isnull filter value is True, combine the two filters using the | operator and assign it to the constructed expense filter
                constructed_expense_filter = Q(**filter1) | Q(**filter2)
            else:
                # If the isnull filter value is False, invert the exact filter using the ~Q operator and assign it to the constructed expense filter
                constructed_expense_filter = ~Q(**filter2)
    # for category non-custom field with not_in as operator, to check this later on
    elif expense_filter.condition == 'category' and expense_filter.operator == 'not_in' and not expense_filter.is_custom:
        # construct the filter
        filter1 = {
            f'{expense_filter.condition}__in': expense_filter.values
        }
        # Invert the filter using the ~Q operator and assign it to the constructed expense filter
        constructed_expense_filter = ~Q(**filter1)
    # For all non-custom fields
    else:
        # Construct the filter for the non-custom field
        filter1 = {
            f'{expense_filter.condition}__{expense_filter.operator}':
                expense_filter.values[0] if len(expense_filter.values) == 1 and expense_filter.operator != 'in'
                else expense_filter.values
        }
        # Assign the constructed filter to the constructed expense filter
        constructed_expense_filter = Q(**filter1)

    # Return the constructed expense filter
    return constructed_expense_filter


def assert_valid_request(workspace_id:int, fyle_org_id:str):
    """
    Assert if the request is valid by checking
    the url_workspace_id and fyle_org_id workspace
    """
    workspace = Workspace.objects.get(fyle_org_id=fyle_org_id)
    if workspace.id != workspace_id:
        raise ValidationError('Workspace mismatch')


class AdvanceSearchFilter(django_filters.FilterSet):
    def filter_queryset(self, queryset):
        or_filtered_queryset = queryset.none()
        or_filter_fields = getattr(self.Meta, 'or_fields', [])
        or_field_present = False

        for field_name in self.Meta.fields:
            value = self.data.get(field_name)
            if value:
                if field_name == 'is_skipped':
                    value = True if str(value) == 'true' else False
                filter_instance = self.filters[field_name]
                queryset = filter_instance.filter(queryset, value)

        for field_name in or_filter_fields:
            value = self.data.get(field_name)
            if value:
                or_field_present = True
                filter_instance = self.filters[field_name]
                field_filtered_queryset = filter_instance.filter(queryset, value)
                or_filtered_queryset |= field_filtered_queryset

        if or_field_present:
            queryset = queryset & or_filtered_queryset
            return queryset

        return queryset


class ExpenseGroupSearchFilter(AdvanceSearchFilter):
    exported_at__gte = django_filters.DateTimeFilter(lookup_expr='gte', field_name='exported_at')
    exported_at__lte = django_filters.DateTimeFilter(lookup_expr='lte', field_name='exported_at')
    tasklog__status = django_filters.CharFilter()
    expenses__expense_number = django_filters.CharFilter(field_name='expenses__expense_number', lookup_expr='icontains')
    expenses__employee_name = django_filters.CharFilter(field_name='expenses__employee_name', lookup_expr='icontains')
    expenses__employee_email = django_filters.CharFilter(field_name='expenses__employee_email', lookup_expr='icontains')
    expenses__claim_number = django_filters.CharFilter(field_name='expenses__claim_number', lookup_expr='icontains')

    class Meta:
        model = ExpenseGroup
        fields = ['exported_at__gte', 'exported_at__lte', 'tasklog__status']
        or_fields = ['expenses__expense_number', 'expenses__employee_name', 'expenses__employee_email', 'expenses__claim_number']


class ExpenseSearchFilter(AdvanceSearchFilter):
    org_id = django_filters.CharFilter()
    is_skipped = django_filters.BooleanFilter()
    updated_at__gte = django_filters.DateTimeFilter(lookup_expr='gte', field_name='updated_at')
    updated_at__lte = django_filters.DateTimeFilter(lookup_expr='lte', field_name='updated_at')
    expense_number = django_filters.CharFilter(field_name='expense_number', lookup_expr='icontains')
    employee_name = django_filters.CharFilter(field_name='employee_name', lookup_expr='icontains')
    employee_email = django_filters.CharFilter(field_name='employee_email', lookup_expr='icontains')
    claim_number = django_filters.CharFilter(field_name='claim_number', lookup_expr='icontains')

    class Meta:
        model = Expense
        fields = ['org_id', 'is_skipped', 'updated_at__gte', 'updated_at__lte']
        or_fields = ['expense_number', 'employee_name', 'employee_email', 'claim_number']
