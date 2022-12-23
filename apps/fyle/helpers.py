import json
import requests
from datetime import datetime, timezone
from fyle_integrations_platform_connector import PlatformConnector
import logging

from django.utils.module_loading import import_string
from django.conf import settings
from django.db.models import Q

from apps.fyle.models import ExpenseGroupSettings,ExpenseFilter
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import FyleCredential, Workspace

logger = logging.getLogger(__name__)


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

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        raise Exception(response.text)


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

    if (corporate_credit_card_expenses_object == 'EXPENSE REPORT' or reimbursable_expenses_object in ['EXPENSE REPORT', 'JOURNAL ENTRY']) and not expense_group_settings.import_card_credits:
        import_card_credits = True
    elif (corporate_credit_card_expenses_object != 'EXPENSE REPORT' and reimbursable_expenses_object not in ['EXPENSE REPORT', 'JOURNAL ENTRY']) and expense_group_settings.import_card_credits:
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
        sync_dimensions(fyle_credentials, workspace.id)
        return True

    return False


def sync_dimensions(fyle_credentials: FyleCredential, workspace_id: int) -> None:
    platform = PlatformConnector(fyle_credentials)

    platform.import_fyle_dimensions(import_taxes=True)
   

def construct_expense_filter(expense_filter:ExpenseFilter):
    constructed_expense_filter = {}
    if expense_filter.is_custom and expense_filter.operator != 'isnull':
        filter1 = {
            'custom_properties__{0}__{1}'.format(expense_filter.condition, expense_filter.operator): expense_filter.values if len(expense_filter.values) > 1 else expense_filter.values[0]
        }
        constructed_expense_filter = Q(**filter1)

    elif expense_filter.is_custom and expense_filter.operator == 'isnull':
        expense_filter_value: bool = True if expense_filter.values[0].lower() == 'true' else False
        filter1 = {
            'custom_properties__{0}__{1}'.format(expense_filter.condition, expense_filter.operator): expense_filter_value
        }
        filter2 = {
            'custom_properties__{0}__exact'.format(expense_filter.condition): None
        }
        if expense_filter_value == True:
            constructed_expense_filter = Q(**filter1) | Q(**filter2)
        else:
            constructed_expense_filter = ~Q(**filter2)

    else:
        filter1 = {
            '{0}__{1}'.format(expense_filter.condition, expense_filter.operator):expense_filter.values if len(expense_filter.values) > 1 else expense_filter.values[0]
        }
        constructed_expense_filter = Q(**filter1)

    return constructed_expense_filter