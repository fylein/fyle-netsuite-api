import logging
from typing import List, Dict
import traceback
from datetime import datetime

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
from fyle_accounting_library.fyle_platform.branding import feature_configuration
from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum
from fyle_accounting_library.fyle_platform.helpers import (
    get_expense_import_states,
    filter_expenses_based_on_state
)
from apps.workspaces.models import (
    FyleCredential,
    LastExportDetail,
    Workspace,
    Configuration,
    WorkspaceSchedule
)
from apps.tasks.models import Error, TaskLog
from .models import Expense, ExpenseFilter, ExpenseGroup, ExpenseGroupSettings
from .helpers import construct_expense_filter_query, update_task_log_post_import
from .helpers import (
    get_filter_credit_expenses,
    get_source_account_type,
    get_fund_source,
    handle_import_exception
)
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


def create_expense_groups(workspace_id: int, fund_source: List[str], task_log: TaskLog | None, imported_from: ExpenseImportSourceEnum):
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
            last_synced_at = workspace.last_synced_at if imported_from != ExpenseImportSourceEnum.CONFIGURATION_UPDATE else None
            ccc_last_synced_at = workspace.ccc_last_synced_at if imported_from != ExpenseImportSourceEnum.CONFIGURATION_UPDATE else None
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
                    settled_at=(last_synced_at if expense_group_settings.expense_state == 'PAYMENT_PROCESSING' else None),
                    filter_credit_expenses=False,
                    last_paid_at=(last_synced_at if expense_group_settings.expense_state == 'PAID' else None)
                ))

            if workspace.last_synced_at or expenses:
                workspace.last_synced_at = datetime.now()
                reimbursable_expenses_count = len(expenses)

            if 'CCC' in fund_source:
                expenses.extend(platform.expenses.get(
                    source_account_type=['PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT'],
                    state=expense_group_settings.ccc_expense_state,
                    settled_at=(ccc_last_synced_at if expense_group_settings.ccc_expense_state == 'PAYMENT_PROCESSING' else None),
                    approved_at=(ccc_last_synced_at if expense_group_settings.ccc_expense_state == 'APPROVED' else None),
                    filter_credit_expenses=False,
                    last_paid_at=(ccc_last_synced_at if expense_group_settings.ccc_expense_state == 'PAID' else None)
                ))

            if workspace.ccc_last_synced_at or len(expenses) != reimbursable_expenses_count:
                workspace.ccc_last_synced_at = datetime.now()

            if imported_from != ExpenseImportSourceEnum.CONFIGURATION_UPDATE:
                workspace.save()

            group_expenses_and_save(expenses, task_log, workspace, imported_from=imported_from, filter_credit_expenses=filter_credit_expenses)

    except FyleCredential.DoesNotExist:
        logger.info("Fyle credentials not found %s", workspace_id)
        update_task_log_post_import(
            task_log,
            'FAILED',
            "Fyle credentials do not exist in workspace"
        )

    except InvalidTokenError:
        logger.info("Invalid Token for Fyle")
        update_task_log_post_import(
            task_log,
            'FAILED',
            "Invalid Fyle credentials"
        )

    except (RetryException, InternalServerError) as e:
        error_msg = f"Fyle {e.__class__.__name__} occurred"
        logger.info("%s in workspace_id: %s", error_msg, workspace_id)
        update_task_log_post_import(
            task_log,
            'FATAL' if isinstance(e, RetryException) else 'FAILED',
            error_msg
        )

    except Exception:
        error = traceback.format_exc()
        logger.exception(
            "Something unexpected happened workspace_id: %s",
            workspace_id
        )
        update_task_log_post_import(task_log, 'FATAL', error=error)


def skip_expenses_and_post_accounting_export_summary(expense_ids: List[int], workspace: Workspace):
    """
    Skip expenses and post accounting export summary
    :param expense_ids: List of expense ids
    :param workspace: Workspace object
    :return: None
    """
    skipped_expenses = mark_expenses_as_skipped(Q(), expense_ids, workspace)
    if skipped_expenses:
        try:
            post_accounting_export_summary(workspace_id=workspace.id, expense_ids=[expense.id for expense in skipped_expenses])
        except Exception:
            logger.exception('Error posting accounting export summary for workspace_id: %s', workspace.id)


def group_expenses_and_save(
    expenses: List[Dict],
    task_log: TaskLog | None,
    workspace: Workspace,
    imported_from: ExpenseImportSourceEnum = None,
    filter_credit_expenses: bool = False
):
    """
    Group expenses and save them as expense groups
    :param expenses: List of expenses
    :param task_log: Task log object
    :param workspace: Workspace object
    :param imported_from: Imported from
    :param filter_credit_expenses: Filter credit expenses
    """
    expense_filters = ExpenseFilter.objects.filter(workspace_id=workspace.id).order_by('rank')
    configuration: Configuration = Configuration.objects.get(workspace_id=workspace.id)

    expense_objects = Expense.create_expense_objects(expenses, workspace.id, imported_from=imported_from)

    # Step 1: Mark negative expenses as skipped if filter_credit_expenses is True
    if filter_credit_expenses:
        negative_expense_ids = [e.id for e in expense_objects if e.amount < 0 and not e.is_skipped]
        if negative_expense_ids:
            expense_objects = [e for e in expense_objects if e.id not in negative_expense_ids] 
            skip_expenses_and_post_accounting_export_summary(negative_expense_ids, workspace)

    # Skip reimbursable expenses if reimbursable expense settings is not configured
    if not configuration.reimbursable_expenses_object:
        reimbursable_expense_ids = [e.id for e in expense_objects if e.fund_source == 'PERSONAL']

        if reimbursable_expense_ids:
            expense_objects = [e for e in expense_objects if e.id not in reimbursable_expense_ids]
            skip_expenses_and_post_accounting_export_summary(reimbursable_expense_ids, workspace)

    # Skip corporate credit card expenses if corporate credit card expense settings is not configured
    if not configuration.corporate_credit_card_expenses_object:
        ccc_expense_ids = [e.id for e in expense_objects if e.fund_source == 'CCC']

        if ccc_expense_ids:
            expense_objects = [e for e in expense_objects if e.id not in ccc_expense_ids]
            skip_expenses_and_post_accounting_export_summary(ccc_expense_ids, workspace)

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

    if task_log:
        task_log.status = 'COMPLETE'
        task_log.updated_at = datetime.now()
        task_log.save(update_fields=['status', 'updated_at'])


def import_and_export_expenses(report_id: str, org_id: str, is_state_change_event: bool, report_state: str = None, imported_from: ExpenseImportSourceEnum = None) -> None:
    """
    Import and export expenses
    :param report_id: report id
    :param org_id: org id
    :return: None
    """
    logger.info('Import and export expenses report_id: %s, org_id: %s', report_id, org_id)
    task_log = None
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
            if imported_from == ExpenseImportSourceEnum.DIRECT_EXPORT:
                source_account_type = ['PERSONAL_CASH_ACCOUNT', 'PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT']
            else:
                source_account_type = get_source_account_type(fund_source)
            filter_credit_expenses = get_filter_credit_expenses(expense_group_settings)

            task_log, _ = TaskLog.objects.update_or_create(workspace_id=workspace.id, type='FETCHING_EXPENSES', defaults={'status': 'IN_PROGRESS'})

            platform = PlatformConnector(fyle_credentials)
            expenses = platform.expenses.get(
                source_account_type,
                filter_credit_expenses=False,
                report_id=report_id,
                import_states=(import_states if is_state_change_event else None)
            )

            if is_state_change_event:
                expenses = filter_expenses_based_on_state(expenses, expense_group_settings)

            group_expenses_and_save(expenses, task_log, workspace, imported_from=imported_from, filter_credit_expenses=filter_credit_expenses)

        # Export only selected expense groups
        expense_ids = Expense.objects.filter(report_id=report_id, org_id=org_id).values_list('id', flat=True)
        expense_groups = ExpenseGroup.objects.filter(expenses__id__in=[expense_ids], workspace_id=workspace.id, exported_at__isnull=True).distinct('id').values('id')
        expense_group_ids = [expense_group['id'] for expense_group in expense_groups]

        if len(expense_group_ids):
            if is_state_change_event:
                # Trigger export immediately for customers who have enabled real time export
                is_real_time_export_enabled = WorkspaceSchedule.objects.filter(workspace_id=workspace.id, is_real_time_export_enabled=True).exists()

                # Don't allow real time export if it's not supported for the branded app / setting not enabled
                if not is_real_time_export_enabled or not feature_configuration.feature.real_time_export_1hr_orgs:
                    return

            logger.info(f'Exporting expenses for workspace {workspace.id} with expense group ids {expense_group_ids}, triggered by {imported_from}')
            export_to_netsuite(
                workspace_id=workspace.id,
                expense_group_ids=expense_group_ids,
                triggered_by=imported_from
            )

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
                    (last_export_detail.failed_expense_groups_count or 0) - deleted_failed_expense_groups_count
                )
                last_export_detail.total_expense_groups_count = max(
                    0,
                    (last_export_detail.total_expense_groups_count or 0) - deleted_total_expense_groups_count
                )
                last_export_detail.save()
            try:
                post_accounting_export_summary(workspace_id=workspace.id, expense_ids=[expense.id for expense in skipped_expenses])
            except Exception:
                logger.exception('Error posting accounting export summary for workspace_id: %s', workspace.id)
