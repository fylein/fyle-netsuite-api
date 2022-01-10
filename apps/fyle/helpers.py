from datetime import datetime, timezone
import logging
from typing import List

from sentry_sdk import capture_message
from django.utils.module_loading import import_string

from apps.fyle.models import ExpenseGroupSettings
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import FyleCredential, Workspace

from apps.fyle.connector import FyleConnector
from fyle_integrations_platform_connector import PlatformConnector

logger = logging.getLogger(__name__)
logger.level = logging.INFO

def compare_tpa_and_platform_expenses(tpa_expenses: List[dict], platform_expenses: List[dict], workspace_id: int) -> None:
    """
    Compare TPA expenses and platform expenses.
    """
    if len(tpa_expenses) != len(platform_expenses):
        # POST to sentry
        logger.error('count is different {} - {}'.format(len(tpa_expenses), len(platform_expenses)))
        capture_message(
            'PLATFORM MIGRATION\nCount is different - {} - {}\nWorkspace ID - {}'.format(
                len(tpa_expenses), len(platform_expenses), workspace_id
            )
        )
    tpa_expenses_ids = [expense['id'] for expense in tpa_expenses]
    platform_expenses_ids = [expense['id'] for expense in platform_expenses]

    missed_expense_ids = list(set(tpa_expenses_ids).difference(platform_expenses_ids))
    if missed_expense_ids:
        # POST to sentry
        capture_message('PLATFORM MIGRATION\nMissed_expense_ids - {}\nWorkspace ID - {}'.format(
            missed_expense_ids, workspace_id
        ))
        logger.error('missed_expense_ids {}'.format(missed_expense_ids))


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


def update_import_card_credits_flag(corporate_credit_card_expenses_object: str, workspace_id: int) -> None:
    """
    set import_card_credits flag to True in ExpenseGroupSettings
    :param corporate_credit_card_expenses_object: Corporate credit card expenses object
    :param workspace_id: Workspace id
    return: None
    """
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    import_card_credits = None

    if corporate_credit_card_expenses_object == 'EXPENSE REPORT' and not expense_group_settings.import_card_credits:
        import_card_credits = True
    elif corporate_credit_card_expenses_object != 'EXPENSE REPORT' and expense_group_settings.import_card_credits:
        import_card_credits = False

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


def check_interval_and_sync_dimension(workspace: Workspace, refresh_token: str) -> bool:
    """
    Check sync interval and sync dimension
    :param workspace: Workspace Instance
    :param refresh_token: Refresh token of an org

    return: True/False based on sync
    """
    if workspace.source_synced_at:
        time_interval = datetime.now(timezone.utc) - workspace.source_synced_at

    if workspace.source_synced_at is None or time_interval.days > 0:
        sync_dimensions(refresh_token, workspace.id)
        return True

    return False


def sync_dimensions(refresh_token: str, workspace_id: int) -> None:
    fyle_connection = import_string('apps.fyle.connector.FyleConnector')(refresh_token, workspace_id)
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    fyle_platform_connection = PlatformConnector(fyle_credentials)
    dimensions = [
        'employees', 'categories', 'cost_centers',
        'projects', 'expense_custom_fields'
    ]

    platform_dimensions = ['tax_groups']

    for dimension in dimensions:
        try:
            sync = getattr(fyle_connection, 'sync_{}'.format(dimension))
            sync()
        except Exception as exception:
            logger.exception(exception)

    for platform_dimension in platform_dimensions:
        try:
            sync_platform = getattr(fyle_platform_connection, '{}.sync'.format(platform_dimension))
            sync_platform()
        except Exception as exception:
            logger.exception(exception)
