from datetime import datetime, timezone
import logging

from django.utils.module_loading import import_string

from apps.fyle.models import ExpenseGroupSettings
from apps.workspaces.models import Workspace

logger = logging.getLogger(__name__)


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


def update_import_card_credits_flag(workspace_id: int):
    """
    set import_card_credits flag to True in ExpenseGroupSettings
    :param workspace_id: Workspace id
    return: None
    """
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    expense_group_settings.import_card_credits = True
    expense_group_settings.save()


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
    dimensions = [
        'employees', 'categories', 'cost_centers',
        'projects', 'expense_custom_fields'
    ]

    for dimension in dimensions:
        try:
            sync = getattr(fyle_connection, 'sync_{}'.format(dimension))
            sync()
        except Exception as exception:
            logger.exception(exception)
