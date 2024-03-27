import json
import traceback
import requests
from datetime import datetime, timezone
from fyle_integrations_platform_connector import PlatformConnector
import logging

from django.conf import settings
from django.db.models import Q
from fyle_accounting_mappings.models import ExpenseAttribute

from apps.fyle.models import ExpenseGroupSettings, ExpenseFilter, ExpenseGroup, Expense
from apps.tasks.models import TaskLog
from apps.workspaces.models import FyleCredential, Workspace, Configuration
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import FyleCredential, Workspace, Configuration
from typing import List, Union

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
        fund_source__in=fund_source
    ).values_list('id', flat=True)
    
    return expense_group_ids


def post_request(url, body, refresh_token=None):
    """
    Create a HTTP post request.
    """
    access_token = None
    api_headers = {}
    if refresh_token:
        access_token = get_access_token(refresh_token)

        api_headers['content-type'] = 'application/json'
        api_headers['Authorization'] = 'Bearer {0}'.format(access_token)

    response = requests.post(
        url,
        headers=api_headers,
        data=body
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
        'content-type': 'application/json',
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


def check_interval_and_sync_dimension(workspace: Workspace, fyle_credentials: FyleCredential) -> bool:
    """
    Check sync interval and sync dimension
    :param workspace: Workspace Instance
    :param refresh_token: Refresh token of an org

    return: True/False based on sync
    """
    if workspace.source_synced_at:
        time_interval = datetime.now(timezone.utc) - workspace.source_synced_at

    if workspace.source_synced_at is None or time_interval.days > 0:
        sync_dimensions(fyle_credentials)
        return True

    return False


def sync_dimensions(fyle_credentials: FyleCredential, is_export: bool = False) -> None:
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

def construct_expense_filter_query(expense_filters: List[ExpenseFilter]):
    final_filter = None
    for expense_filter in expense_filters:
        constructed_expense_filter = construct_expense_filter(expense_filter)
        if expense_filter.rank == 1:
            final_filter = (constructed_expense_filter)
        elif expense_filter.rank != 1 and join_by == 'AND':
            final_filter = final_filter & (constructed_expense_filter)
        elif expense_filter.rank != 1 and join_by == 'OR':
            final_filter = final_filter | (constructed_expense_filter)

        join_by = expense_filter.join_by

    return final_filter

def construct_expense_filter(expense_filter: ExpenseFilter):
    constructed_expense_filter = {}
    if expense_filter.is_custom and expense_filter.operator != 'isnull':
        #This block is for custom-field with not null check
        if expense_filter.custom_field_type == 'SELECT' and expense_filter.operator == 'not_in':
            filter1 = {
                'custom_properties__{0}__{1}'.format(
                    expense_filter.condition,
                    'in'
                ): expense_filter.values
            }
            constructed_expense_filter = ~Q(**filter1)
        else:
            if expense_filter.custom_field_type == 'NUMBER':
                expense_filter.values = [int(expense_filter_value) for expense_filter_value in expense_filter.values]

            filter1 = {
                'custom_properties__{0}__{1}'.format(
                    expense_filter.condition,
                    expense_filter.operator
                ): expense_filter.values if len(expense_filter.values) > 1 or expense_filter.operator == 'in' else expense_filter.values[0]
            }
            constructed_expense_filter = Q(**filter1)

    elif expense_filter.is_custom and expense_filter.operator == 'isnull':
        #This block is for custom-field is null check
        expense_filter_value: bool = True if expense_filter.values[0].lower() == 'true' else False
        filter1 = {
            'custom_properties__{0}__{1}'.format(
                expense_filter.condition,
                expense_filter.operator
            ): expense_filter_value
        }
        filter2 = {
            'custom_properties__{0}__exact'.format(expense_filter.condition): None
        }
        if expense_filter_value == True:
            #if isnull=True
            constructed_expense_filter = Q(**filter1) | Q(**filter2)
        else:
            #if isnull=False
            constructed_expense_filter = ~Q(**filter2)

    else:
        #This block is for all the non-custom-fields
        filter1 = {
            '{0}__{1}'.format(
                expense_filter.condition,
                expense_filter.operator
            ):expense_filter.values if len(expense_filter.values) > 1 or expense_filter.operator == 'in' else expense_filter.values[0]
        }
        constructed_expense_filter = Q(**filter1)

    return constructed_expense_filter
