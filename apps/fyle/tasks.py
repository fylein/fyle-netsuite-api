import logging
from typing import List, Dict
import traceback
from datetime import datetime, timezone

from django.db import transaction
from django.db.models import Q
from django_q.tasks import async_task

from fyle_integrations_platform_connector import PlatformConnector
from fyle_integrations_platform_connector.apis.expenses import Expenses as FyleExpenses
from fyle.platform.exceptions import (
    RetryException,
    InternalServerError,
    InvalidTokenError
)
from fyle_accounting_library.fyle_platform.helpers import get_expense_import_states, filter_expenses_based_on_state
from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum

from apps.workspaces.models import FyleCredential, LastExportDetail, Workspace, Configuration
from apps.tasks.models import Error, TaskLog

from .models import Expense, ExpenseFilter, ExpenseGroup, ExpenseGroupSettings
from .helpers import construct_expense_filter_query
from .helpers import construct_expense_filter_query, get_filter_credit_expenses, get_source_account_type, get_fund_source, handle_import_exception
from apps.workspaces.actions import export_to_netsuite
from .actions import (
    mark_expenses_as_skipped,
    post_accounting_export_summary
)

logger = logging.getLogger(__name__)
logger.level = logging.INFO

SOURCE_ACCOUNT_MAP = {
    'PERSONAL': 'PERSONAL_CASH_ACCOUNT',
    'CCC': 'PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT'
}

def get_task_log_and_fund_source(workspace_id: int):
    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=workspace_id,
        type='FETCHING_EXPENSES',
        defaults={
           'status': 'IN_PROGRESS'
        }
    )

    configuration = Configuration.objects.get(workspace_id=workspace_id)
    fund_source = []

    if configuration.reimbursable_expenses_object:
        fund_source.append('PERSONAL')
    if configuration.corporate_credit_card_expenses_object:
        fund_source.append('CCC')

    return task_log, fund_source

def schedule_expense_group_creation(workspace_id: int):
    """
    Schedule Expense group creation
    :param workspace_id: Workspace id
    :param user: User email
    :return: None
    """
    task_log, fund_source = get_task_log_and_fund_source(workspace_id)

    async_task('apps.fyle.tasks.create_expense_groups', workspace_id, fund_source, task_log)


def create_expense_groups(workspace_id: int, fund_source: List[str], task_log: TaskLog, imported_from: ExpenseImportSourceEnum):
    """
    Create expense groups
    :param task_log: Task log object
    :param workspace_id: workspace id
    :param state: expense state
    :param fund_source: expense fund source
    """
    try:
        with transaction.atomic():
            expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
            workspace = Workspace.objects.get(pk=workspace_id)
            last_synced_at = workspace.last_synced_at
            ccc_last_synced_at = workspace.ccc_last_synced_at
            fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)

            platform = PlatformConnector(fyle_credentials)
            source_account_type = []

            for source in fund_source:
                source_account_type.append(SOURCE_ACCOUNT_MAP[source])

            filter_credit_expenses = True
            if expense_group_settings.import_card_credits:
                filter_credit_expenses = False

            expenses = []
            reimbursable_expenses_count = 0

            if 'PERSONAL' in fund_source:
                expenses.extend(platform.expenses.get(
                    source_account_type=['PERSONAL_CASH_ACCOUNT'],
                    state=expense_group_settings.expense_state,
                    settled_at=last_synced_at if expense_group_settings.expense_state == 'PAYMENT_PROCESSING' else None,
                    filter_credit_expenses=filter_credit_expenses,
                    last_paid_at=last_synced_at if expense_group_settings.expense_state == 'PAID' else None
                ))

            if workspace.last_synced_at or expenses:
                workspace.last_synced_at = datetime.now()
                reimbursable_expenses_count = len(expenses)

            if 'CCC' in fund_source:
                expenses.extend(platform.expenses.get(
                    source_account_type=['PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT'],
                    state=expense_group_settings.ccc_expense_state,
                    settled_at=ccc_last_synced_at if expense_group_settings.ccc_expense_state == 'PAYMENT_PROCESSING' else None,
                    approved_at=ccc_last_synced_at if expense_group_settings.ccc_expense_state == 'APPROVED' else None,
                    filter_credit_expenses=filter_credit_expenses,
                    last_paid_at=ccc_last_synced_at if expense_group_settings.ccc_expense_state == 'PAID' else None
                ))

            if workspace.ccc_last_synced_at or len(expenses) != reimbursable_expenses_count:
                workspace.ccc_last_synced_at = datetime.now()

            workspace.save()

            group_expenses_and_save(expenses, task_log, workspace, imported_from=imported_from)

    except (FyleCredential.DoesNotExist, InvalidTokenError):
        logger.info('Fyle credentials not found / Invalid token %s', workspace_id)
        task_log.detail = {
            'message': 'Fyle credentials do not exist in workspace / Invalid token'
        }
        task_log.status = 'FAILED'
        task_log.save()

    except RetryException:
        logger.info('Fyle Retry Exception occured in workspace_id: %s', workspace_id)
        task_log.detail = {
            'message': 'Fyle Retry Exception occured'
        }
        task_log.status = 'FATAL'
        task_log.save()

    except InternalServerError:
        logger.info('Fyle Internal Server Error occured in workspace_id: %s', workspace_id)
        task_log.detail = {
            'message': 'Fyle Internal Server Error occured'
        }
        task_log.status = 'FAILED'
        task_log.save()

    except Exception:
        error = traceback.format_exc()
        task_log.detail = {
            'error': error
        }
        task_log.status = 'FATAL'
        task_log.save()
        logger.exception('Something unexpected happened workspace_id: %s %s', task_log.workspace_id, task_log.detail)


def group_expenses_and_save(expenses: List[Dict], task_log: TaskLog, workspace: Workspace, imported_from: ExpenseImportSourceEnum = None):
    expense_objects = Expense.create_expense_objects(expenses, workspace.id, imported_from=imported_from)
    expense_filters = ExpenseFilter.objects.filter(workspace_id=workspace.id).order_by('rank')
    configuration : Configuration = Configuration.objects.get(workspace_id=workspace.id)
    filtered_expenses = expense_objects
    if expense_filters:
        expenses_object_ids = [expense_object.id for expense_object in expense_objects]
        final_query = construct_expense_filter_query(expense_filters)
        skipped_expenses = mark_expenses_as_skipped(final_query, expenses_object_ids, workspace)
        if skipped_expenses:
            try:
                post_accounting_export_summary(workspace_id=workspace.id, expense_ids=[expense.id for expense in skipped_expenses])
            except Exception:
                logger.exception('Error posting accounting export summary for workspace_id: %s', workspace.id)

        filtered_expenses = Expense.objects.filter(
            is_skipped=False,
            id__in=expenses_object_ids,
            expensegroup__isnull=True,
            org_id=workspace.fyle_org_id
        )

    skipped_expense_ids = ExpenseGroup.create_expense_groups_by_report_id_fund_source(
        filtered_expenses, configuration, workspace.id
    )

    if skipped_expense_ids:
        skipped_expenses = mark_expenses_as_skipped(final_query=Q(), expenses_object_ids=skipped_expense_ids, workspace=workspace)
        if skipped_expenses:
            try:
                post_accounting_export_summary(workspace_id=workspace.id, expense_ids=[expense.id for expense in skipped_expenses])
            except Exception:
                logger.error('Error posting accounting export summary for workspace_id: %s', workspace.id)

    task_log.status = 'COMPLETE'
    task_log.save()


def import_and_export_expenses(report_id: str, org_id: str, is_state_change_event: bool, report_state: str = None, imported_from: ExpenseImportSourceEnum = None) -> None:
    """
    Import and export expenses
    :param report_id: report id
    :param org_id: org id
    :return: None
    """
    logger.info('Import and export expenses report_id: %s, org_id: %s', report_id, org_id)
    workspace = Workspace.objects.get(fyle_org_id=org_id)
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace.id)

    import_states = get_expense_import_states(expense_group_settings)

    # Don't call API if report state is not in import states, for example customer configured to import only PAID reports but webhook is triggered for APPROVED report (this is only for is_state_change_event webhook calls)
    if is_state_change_event and report_state and report_state not in import_states:
        return

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace.id)

    try:
        with transaction.atomic():
            fund_source = get_fund_source(workspace.id)
            source_account_type = get_source_account_type(fund_source)
            filter_credit_expenses = get_filter_credit_expenses(expense_group_settings)

            task_log, _ = TaskLog.objects.update_or_create(workspace_id=workspace.id, type='FETCHING_EXPENSES', defaults={'status': 'IN_PROGRESS'})

            platform = PlatformConnector(fyle_credentials)
            expenses = platform.expenses.get(
                source_account_type,
                filter_credit_expenses=filter_credit_expenses,
                report_id=report_id,
                import_states=import_states if is_state_change_event else None
            )

            if is_state_change_event:
                expenses = filter_expenses_based_on_state(expenses, expense_group_settings)

            group_expenses_and_save(expenses, task_log, workspace, imported_from=imported_from)

        # Export only selected expense groups
        expense_ids = Expense.objects.filter(report_id=report_id, org_id=org_id).values_list('id', flat=True)
        expense_groups = ExpenseGroup.objects.filter(expenses__id__in=[expense_ids], workspace_id=workspace.id, exported_at__isnull=True).distinct('id').values('id')
        expense_group_ids = [expense_group['id'] for expense_group in expense_groups]

        if len(expense_group_ids) and not is_state_change_event:
            logger.info('Exporting to Netsuite(Direct Export Trigger) workspace_id: %s, expense_group_ids: %s', workspace.id, expense_group_ids)
            export_to_netsuite(workspace.id, None, expense_group_ids, triggered_by=imported_from)

    except Configuration.DoesNotExist:
        logger.info('Configuration not found %s', workspace.id)
        if not task_log:
            task_log, _ = TaskLog.objects.update_or_create(workspace_id=workspace.id, type='FETCHING_EXPENSES', defaults={'status': 'IN_PROGRESS'})

        task_log.detail = {'message': 'Configuration not found'}
        task_log.status = 'FAILED'
        task_log.save()

    except Exception:
        if not task_log:
            task_log, _ = TaskLog.objects.update_or_create(workspace_id=workspace.id, type='FETCHING_EXPENSES', defaults={'status': 'IN_PROGRESS'})

        handle_import_exception(task_log)


def update_non_exported_expenses(data: Dict) -> None:
    """
    To update expenses not in COMPLETE, IN_PROGRESS state
    """
    expense_state = None
    org_id = data['org_id']
    expense_id = data['id']
    workspace = Workspace.objects.get(fyle_org_id=org_id)
    expense = Expense.objects.filter(workspace_id=workspace.id, expense_id=expense_id).first()

    if expense:
        if 'state' in expense.accounting_export_summary:
            expense_state = expense.accounting_export_summary['state']
        else:
            expense_state = 'NOT_EXPORTED'

        if expense_state and expense_state not in ['COMPLETE', 'IN_PROGRESS']:
            expense_obj = []
            expense_obj.append(data)
            expense_objects = FyleExpenses().construct_expense_object(expense_obj, expense.workspace_id)
            Expense.create_expense_objects(
                expense_objects, expense.workspace_id, skip_update=True
            )


def re_run_skip_export_rule(workspace: Workspace) -> None:
    """
    Skip expenses before export
    :param workspace_id: Workspace id
    :return: None
    """
    expense_filters = ExpenseFilter.objects.filter(workspace_id=workspace.id).order_by('rank')
    if expense_filters:
        filtered_expense_query = construct_expense_filter_query(expense_filters)
        # Get all expenses matching the filter query, excluding those in COMPLETE state
        expenses = Expense.objects.filter(
            filtered_expense_query, workspace_id=workspace.id, is_skipped=False
        ).filter(
            Q(accounting_export_summary={}) | ~Q(accounting_export_summary__state="COMPLETE")
        )
        expense_ids = list(expenses.values_list('id', flat=True))
        skipped_expenses = mark_expenses_as_skipped(
            filtered_expense_query,
            expense_ids,
            workspace
        )
        if skipped_expenses:
            # Get all expense groups that contain any of the skipped expenses
            expense_groups = ExpenseGroup.objects.filter(
                exported_at__isnull=True,
                workspace_id=workspace.id,
                expenses__in=skipped_expenses)

            deleted_failed_expense_groups_count = 0
            deleted_total_expense_groups_count = 0

            for expense_group in expense_groups:
                task_log = TaskLog.objects.filter(
                    workspace_id=workspace.id,
                    expense_group_id=expense_group.id
                ).first()
                if task_log:
                    if task_log.status != 'COMPLETE':
                        deleted_failed_expense_groups_count += 1
                    logger.info('Deleting task log for expense group %s before export', expense_group.id)
                    task_log.delete()

                error = Error.objects.filter(
                    workspace_id=workspace.id,
                    expense_group_id=expense_group.id,
                ).first()
                if error:
                    logger.info('Deleting Netsuite error for expense group %s before export', expense_group.id)
                    error.delete()

                expense_group.expenses.remove(*skipped_expenses)
                if not expense_group.expenses.exists():
                    logger.info('Deleting empty expense group %s before export', expense_group.id)
                    expense_group.delete()
                    deleted_total_expense_groups_count += 1

            last_export_detail = LastExportDetail.objects.filter(workspace_id=workspace.id).first()
            if last_export_detail:
                last_export_detail.failed_expense_groups_count = max(
                    0,
                    last_export_detail.failed_expense_groups_count - deleted_failed_expense_groups_count
                )
                last_export_detail.total_expense_groups_count = max(
                    0,
                    last_export_detail.total_expense_groups_count - deleted_total_expense_groups_count
                )
                last_export_detail.save()
