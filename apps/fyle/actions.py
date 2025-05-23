from datetime import datetime, timezone
from typing import List
import logging

from django.conf import settings
from django.db.models import Q

from fyle_integrations_platform_connector import PlatformConnector
from fyle.platform.internals.decorators import retry
from fyle.platform.exceptions import InternalServerError, RetryException

from apps.fyle.models import Expense, ExpenseGroup
from apps.workspaces.models import Workspace, FyleCredential, Configuration
from apps.fyle.helpers import get_updated_accounting_export_summary, get_batched_expenses
from fyle_netsuite_api.logging_middleware import get_logger, get_caller_info


logger = logging.getLogger(__name__)
logger.level = logging.INFO


def __get_redirection_url(workspace_id: str, state: str) -> str:
    map = {
        'IN_PROGRESS': '{}/main/dashboard',
        'ERROR': '{}/main/dashboard',
        'SKIPPED': '{}/main/export_log',
        'DELETED': '{}/main/dashboard'
    }
    if settings.BRAND_ID == 'fyle':
        return map[state].format(settings.NETSUITE_INTEGRATION_APP_URL, workspace_id)

    if state == 'SKIPPED':
        return '{}/main/export_log'.format(settings.NETSUITE_INTEGRATION_APP_URL)

    return '{}/main/dashboard'.format(settings.NETSUITE_INTEGRATION_APP_URL)


def __bulk_update_expenses(expense_to_be_updated: List[Expense]) -> None:
    """
    Bulk update expenses
    :param expense_to_be_updated: expenses to be updated
    :return: None
    """
    if expense_to_be_updated:
        for expense in expense_to_be_updated:
            expense.updated_at = datetime.now(timezone.utc)

        Expense.objects.bulk_update(expense_to_be_updated, ['is_skipped', 'accounting_export_summary', 'updated_at'], batch_size=50)


def update_expenses_in_progress(in_progress_expenses: List[Expense]) -> None:
    """
    Update expenses in progress in bulk
    :param in_progress_expenses: in progress expenses
    :return: None
    """
    expense_to_be_updated = []
    for expense in in_progress_expenses:
        url = __get_redirection_url(expense.workspace_id, 'IN_PROGRESS')

        expense_to_be_updated.append(
            Expense(
                id=expense.id,
                accounting_export_summary=get_updated_accounting_export_summary(
                    expense.expense_id,
                    'IN_PROGRESS',
                    None,
                    url,
                    False
                )
            )
        )

    __bulk_update_expenses(expense_to_be_updated)


def mark_expenses_as_skipped(final_query: Q, expenses_object_ids: List, workspace: Workspace) -> List[Expense]:
    """
    Mark expenses as skipped in bulk
    :param final_query: final query
    :param expenses_object_ids: expenses object ids
    :param workspace: workspace object
    :return: List of skipped expense objects
    """
    expenses_to_be_skipped = Expense.objects.filter(
        final_query,
        id__in=expenses_object_ids,
        org_id=workspace.fyle_org_id,
        is_skipped=False  # Only mark expenses that aren't already skipped
    )
    skipped_expenses_list = list(expenses_to_be_skipped)
    expense_to_be_updated = []
    for expense in expenses_to_be_skipped:
        expense_to_be_updated.append(
            Expense(
                id=expense.id,
                is_skipped=True,
                accounting_export_summary=get_updated_accounting_export_summary(
                    expense.expense_id,
                    'SKIPPED',
                    None,
                    '{}/main/export_log'.format(settings.NETSUITE_INTEGRATION_APP_URL),
                    False
                )
            )
        )

    if expense_to_be_updated:
        __bulk_update_expenses(expense_to_be_updated)

    # Return the updated expense objects
    return skipped_expenses_list


def mark_accounting_export_summary_as_synced(expenses: List[Expense]) -> None:
    """
    Mark accounting export summary as synced in bulk
    :param expenses: List of expenses
    :return: None
    """
    # Mark all expenses as synced
    expense_to_be_updated = []
    current_time = datetime.now(timezone.utc)
    for expense in expenses:
        expense.accounting_export_summary['synced'] = True
        updated_accounting_export_summary = expense.accounting_export_summary
        expense_to_be_updated.append(
            Expense(
                id=expense.id,
                accounting_export_summary=updated_accounting_export_summary,
                previous_export_state=updated_accounting_export_summary['state'],
                updated_at=current_time
            )
        )

    Expense.objects.bulk_update(expense_to_be_updated, ['accounting_export_summary', 'previous_export_state', 'updated_at'], batch_size=50)


def update_failed_expenses(failed_expenses: List[Expense], is_mapping_error: bool) -> None:
    """
    Update failed expenses
    :param failed_expenses: Failed expenses
    """
    expense_to_be_updated = []
    for expense in failed_expenses:
        error_type = 'MAPPING' if is_mapping_error else 'ACCOUNTING_INTEGRATION_ERROR'
        url = __get_redirection_url(expense.workspace_id, 'ERROR')
        # Skip dummy updates (if it is already in error state with the same error type)
        if not (expense.accounting_export_summary.get('state') == 'ERROR' and \
            expense.accounting_export_summary.get('error_type') == error_type):
            expense_to_be_updated.append(
                Expense(
                    id=expense.id,
                    accounting_export_summary=get_updated_accounting_export_summary(
                        expense.expense_id,
                        'ERROR',
                        error_type,
                        url,
                        False
                    )
                )
            )

    __bulk_update_expenses(expense_to_be_updated)


def update_complete_expenses(exported_expenses: List[Expense], url: str) -> None:
    """
    Update complete expenses
    :param exported_expenses: Exported expenses
    :param url: Export url
    :return: None
    """
    expense_to_be_updated = []
    for expense in exported_expenses:
        expense_to_be_updated.append(
            Expense(
                id=expense.id,
                accounting_export_summary=get_updated_accounting_export_summary(
                    expense.expense_id,
                    'COMPLETE',
                    None,
                    url,
                    False
                )
            )
        )

    __bulk_update_expenses(expense_to_be_updated)


def __handle_post_accounting_export_summary_exception(exception: Exception, workspace_id: int) -> None:
    """
    Handle post accounting export summary exception
    :param exception: Exception
    :param workspace_id: Workspace id
    :return: None
    """
    error_response = exception.__dict__
    expense_to_be_updated = []
    if (
        'message' in error_response and error_response['message'] == 'Some of the parameters are wrong'
        and 'response' in error_response and 'data' in error_response['response'] and error_response['response']['data']
    ):
        logger.info('Error while syncing workspace %s %s',workspace_id, error_response)
        current_time = datetime.now(timezone.utc)
        for expense in error_response['response']['data']:
            url = __get_redirection_url(workspace_id, 'DELETED')

            if expense['message'] == 'Permission denied to perform this action.':
                expense_instance = Expense.objects.get(expense_id=expense['key'], workspace_id=workspace_id)
                expense_to_be_updated.append(
                    Expense(
                        id=expense_instance.id,
                        accounting_export_summary=get_updated_accounting_export_summary(
                            expense_instance.expense_id,
                            'DELETED',
                            None,
                            url,
                            True
                        ),
                        updated_at=current_time
                    )
                )
        if expense_to_be_updated:
            Expense.objects.bulk_update(expense_to_be_updated, ['accounting_export_summary', 'updated_at'], batch_size=50)
    else:
        logger.error('Error while syncing accounting export summary, workspace_id: %s %s', workspace_id, str(error_response))


@retry(n=3, backoff=1, exceptions=InternalServerError)
def bulk_post_accounting_export_summary(platform: PlatformConnector, payload: List[dict]):
    """
    Bulk post accounting export summary with retry of 3 times and backoff of 1 second which handles InternalServerError
    :param platform: Platform connector object
    :param payload: Payload
    :return: None
    """
    platform.expenses.post_bulk_accounting_export_summary(payload)


def create_generator_and_post_in_batches(accounting_export_summary_batches: List[dict], platform: PlatformConnector, workspace_id: int) -> None:
    """
    Create generator and post in batches
    :param accounting_export_summary_batches: Accounting export summary batches
    :param platform: Platform connector object
    :param workspace_id: Workspace id
    :return: None
    """
    for batched_payload in accounting_export_summary_batches:
        try:
            if batched_payload:
                bulk_post_accounting_export_summary(platform, batched_payload)

                batched_expenses = get_batched_expenses(batched_payload, workspace_id)
                mark_accounting_export_summary_as_synced(batched_expenses)
        except RetryException:
            logger.error(
                'Internal server error while posting accounting export summary to Fyle workspace_id: %s',
                workspace_id
            )
        except Exception as exception:
            __handle_post_accounting_export_summary_exception(exception, workspace_id)


def post_accounting_export_summary(workspace_id: int, expense_ids: List = None, fund_source: str = None, is_failed: bool = False) -> None:
    """
    Post accounting export summary to Fyle
    :param org_id: org id
    :param workspace_id: workspace id
    :param fund_source: fund source
    :return: None
    """
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    if configuration.skip_accounting_export_summary_post:
        return
    
    worker_logger = get_logger()
    caller_info = get_caller_info()
    # Iterate through all expenses which are not synced and post accounting export summary to Fyle in batches
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    platform = PlatformConnector(fyle_credentials)
    filters = {
        'workspace_id': workspace_id,
        'accounting_export_summary__synced': False
    }

    if expense_ids:
        filters['id__in'] = expense_ids

    if fund_source:
        filters['fund_source'] = fund_source

    if is_failed:
        filters['accounting_export_summary__state'] = 'ERROR'

    expenses_count = Expense.objects.filter(**filters).count()

    accounting_export_summary_batches = []
    page_size = 20
    for offset in range(0, expenses_count, page_size):
        limit = offset + page_size
        paginated_expenses = Expense.objects.filter(**filters).order_by('id')[offset:limit]

        payload = []

        for expense in paginated_expenses:
            accounting_export_summary = expense.accounting_export_summary
            accounting_export_summary.pop('synced')
            payload.append(expense.accounting_export_summary)

        accounting_export_summary_batches.append(payload)

    worker_logger.info(
        'Called from %s, Posting accounting export summary to Fyle workspace_id: %s, payload: %s',
        caller_info,
        workspace_id,
        accounting_export_summary_batches
    )
    create_generator_and_post_in_batches(accounting_export_summary_batches, platform, workspace_id)


def post_accounting_export_summary_for_skipped_exports(expense_group: ExpenseGroup, workspace_id: int, is_mapping_error: bool = True):
    first_expense = expense_group.expenses.first()
    update_expenses_in_progress([first_expense])
    post_accounting_export_summary(workspace_id=workspace_id, expense_ids=[first_expense.id])
    update_failed_expenses(expense_group.expenses.all(), is_mapping_error)
    post_accounting_export_summary(workspace_id=workspace_id, expense_ids=[expense.id for expense in expense_group.expenses.all()], is_failed=True)
