import logging
from typing import List
from datetime import datetime, timedelta, timezone

from django.db.models import Q
from django_q.tasks import Chain

from apps.fyle.models import ExpenseGroup, Expense
from apps.tasks.models import TaskLog, Error
from apps.workspaces.models import FyleCredential

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def __create_chain_and_run(fyle_credentials: FyleCredential, in_progress_expenses: List[Expense],
        workspace_id: int, chain_tasks: List[dict], fund_source: str) -> None:
    """
    Create chain and run
    :param fyle_credentials: Fyle credentials
    :param in_progress_expenses: List of in progress expenses
    :param workspace_id: workspace id
    :param chain_tasks: List of chain tasks
    :param fund_source: Fund source
    :return: None
    """
    chain = Chain()

    chain.append('apps.netsuite.tasks.update_expense_and_post_summary', in_progress_expenses, workspace_id, fund_source)
    chain.append('apps.fyle.helpers.sync_dimensions', workspace_id, True)

    for task in chain_tasks:
        logger.info('Chain task %s, Chain Expense Group %s, Chain Task Log %s', task['target'], task['expense_group'], task['task_log_id'])
        chain.append(task['target'], task['expense_group'], task['task_log_id'], task['last_export'])

    chain.append('apps.fyle.tasks.post_accounting_export_summary', fyle_credentials.workspace.fyle_org_id, workspace_id, fund_source, True)
    chain.run()


def validate_failing_export(is_auto_export: bool, interval_hours: int, error: Error):
    """
    Validate failing export
    :param is_auto_export: Is auto export
    :param interval_hours: Interval hours
    :param error: Error
    """
    # If auto export is enabled and interval hours is set and error repetition count is greater than 100, export only once a day
    return is_auto_export and interval_hours and error and error.repetition_count > 100 and datetime.now().replace(tzinfo=timezone.utc) - error.updated_at <= timedelta(hours=24)


def schedule_bills_creation(workspace_id: int, expense_group_ids: List[str], is_auto_export: bool, fund_source: str, interval_hours: int):
    """
    Schedule bills creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :return: None
    """
    if expense_group_ids:
        logger.info('Preparing to queue expense groups %s of fund source %s for Bill', expense_group_ids, fund_source)
        expense_groups = ExpenseGroup.objects.filter(
            Q(tasklog__id__isnull=True) | ~Q(tasklog__status__in=['IN_PROGRESS', 'COMPLETE']),
            workspace_id=workspace_id, id__in=expense_group_ids, bill__id__isnull=True, exported_at__isnull=True
        ).all()

        errors = Error.objects.filter(workspace_id=workspace_id, is_resolved=False, expense_group_id__in=expense_group_ids).all()

        chain_tasks = []
        in_progress_expenses = []

        for index, expense_group in enumerate(expense_groups):
            
            error = errors.filter(workspace_id=workspace_id, expense_group=expense_group, is_resolved=False).first()
            skip_export = validate_failing_export(is_auto_export, interval_hours, error)
            if skip_export:
                logger.info('Skipping expense group %s as it has %s errors', expense_group.id, error.repetition_count)
                continue

            task_log, _ = TaskLog.objects.get_or_create(
                workspace_id=expense_group.workspace_id,
                expense_group=expense_group,
                defaults={
                    'status': 'ENQUEUED',
                    'type': 'CREATING_BILL'
                }
            )

            if task_log.status not in ['IN_PROGRESS', 'ENQUEUED']:
                task_log.type = 'CREATING_BILL'
                task_log.status = 'ENQUEUED'
                task_log.save()
            
            last_export = False
            if expense_groups.count() == index + 1:
                last_export = True

            chain_tasks.append({
                    'target': 'apps.netsuite.tasks.create_bill',
                    'expense_group': expense_group,
                    'task_log_id': task_log.id,
                    'last_export': last_export
                    })
            if not (is_auto_export and expense_group.expenses.first().previous_export_state == 'ERROR'):
                in_progress_expenses.extend(expense_group.expenses.all())

        if len(chain_tasks) > 0:
                fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
                __create_chain_and_run(fyle_credentials, in_progress_expenses, workspace_id, chain_tasks, fund_source)


def schedule_credit_card_charge_creation(workspace_id: int, expense_group_ids: List[str], is_auto_export: bool, fund_source: str, interval_hours: int):
    """
    Schedule Credit Card Charge creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :return: None
    """
    if expense_group_ids:
        logger.info('Preparing to queue expense groups %s of fund source %s for Credit Card Charge', expense_group_ids, fund_source)
        expense_groups = ExpenseGroup.objects.filter(
            Q(tasklog__id__isnull=True) | ~Q(tasklog__status__in=['IN_PROGRESS', 'COMPLETE']),
            workspace_id=workspace_id, id__in=expense_group_ids,
            creditcardcharge__id__isnull=True, exported_at__isnull=True
        ).all()

        errors = Error.objects.filter(workspace_id=workspace_id, is_resolved=False, expense_group_id__in=expense_group_ids).all()

        chain_tasks = []
        in_progress_expenses = []

        for index, expense_group in enumerate(expense_groups):
            
            error = errors.filter(workspace_id=workspace_id, expense_group=expense_group, is_resolved=False).first()
            skip_export = validate_failing_export(is_auto_export, interval_hours, error)
            if skip_export:
                logger.info('Skipping expense group %s as it has %s errors', expense_group.id, error.repetition_count)
                continue

            expense_amount = expense_group.expenses.first().amount
            export_type = 'CREATING_CREDIT_CARD_CHARGE'
            if expense_amount < 0:
                export_type = 'CREATING_CREDIT_CARD_REFUND'

            task_log, _ = TaskLog.objects.get_or_create(
                workspace_id=expense_group.workspace_id,
                expense_group=expense_group,
                defaults={
                    'status': 'ENQUEUED',
                    'type': export_type
                }
            )

            if task_log.status not in ['IN_PROGRESS', 'ENQUEUED']:
                task_log.type = export_type
                task_log.status = 'ENQUEUED'
                task_log.save()
            
            last_export = False
            if expense_groups.count() == index + 1:
                last_export = True

            chain_tasks.append({
                    'target': 'apps.netsuite.tasks.create_credit_card_charge',
                    'expense_group': expense_group,
                    'task_log_id': task_log.id,
                    'last_export': last_export
                    })

            if not (is_auto_export and expense_group.expenses.first().previous_export_state == 'ERROR'):
                in_progress_expenses.extend(expense_group.expenses.all())

        if len(chain_tasks) > 0:
            fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
            __create_chain_and_run(fyle_credentials, in_progress_expenses, workspace_id, chain_tasks, fund_source)


def schedule_expense_reports_creation(workspace_id: int, expense_group_ids: List[str], is_auto_export: bool, fund_source: str, interval_hours: int):
    """
    Schedule expense reports creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :return: None
    """
    if expense_group_ids:
        logger.info('Preparing to queue expense groups %s of fund source %s for Expense Report', expense_group_ids, fund_source)
        expense_groups = ExpenseGroup.objects.filter(
            Q(tasklog__id__isnull=True) | ~Q(tasklog__status__in=['IN_PROGRESS', 'COMPLETE']),
            workspace_id=workspace_id, id__in=expense_group_ids,
            expensereport__id__isnull=True, exported_at__isnull=True
        ).all()

        errors = Error.objects.filter(workspace_id=workspace_id, is_resolved=False, expense_group_id__in=expense_group_ids).all()

        chain_tasks = []
        in_progress_expenses = []

        for index, expense_group in enumerate(expense_groups):

            error = errors.filter(workspace_id=workspace_id, expense_group=expense_group, is_resolved=False).first()
            skip_export = validate_failing_export(is_auto_export, interval_hours, error)
            if skip_export:
                logger.info('Skipping expense group %s as it has %s errors', expense_group.id, error.repetition_count)
                continue

            task_log, _ = TaskLog.objects.get_or_create(
                workspace_id=expense_group.workspace_id,
                expense_group=expense_group,
                defaults={
                    'status': 'ENQUEUED',
                    'type': 'CREATING_EXPENSE_REPORT'
                }
            )

            if task_log.status not in ['IN_PROGRESS', 'ENQUEUED']:
                task_log.type = 'CREATING_EXPENSE_REPORT'
                task_log.status = 'ENQUEUED'
                task_log.save()
            
            last_export = False
            if expense_groups.count() == index + 1:
                last_export = True

            chain_tasks.append({
                    'target': 'apps.netsuite.tasks.create_expense_report',
                    'expense_group': expense_group,
                    'task_log_id': task_log.id,
                    'last_export': last_export
                    })

            if not (is_auto_export and expense_group.expenses.first().previous_export_state == 'ERROR'):
                in_progress_expenses.extend(expense_group.expenses.all())

        if len(chain_tasks) > 0:
                fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
                __create_chain_and_run(fyle_credentials, in_progress_expenses, workspace_id, chain_tasks, fund_source)


def schedule_journal_entry_creation(workspace_id: int, expense_group_ids: List[str], is_auto_export: bool, fund_source: str, interval_hours: int):
    """
    Schedule journal entries creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :return: None
    """
    if expense_group_ids:
        logger.info('Preparing to queue expense groups %s of fund source %s Journal Entry', expense_group_ids, fund_source)
        expense_groups = ExpenseGroup.objects.filter(
            Q(tasklog__id__isnull=True) | ~Q(tasklog__status__in=['IN_PROGRESS', 'COMPLETE']),
            workspace_id=workspace_id, id__in=expense_group_ids, journalentry__id__isnull=True, exported_at__isnull=True
        ).all()

        errors = Error.objects.filter(workspace_id=workspace_id, is_resolved=False, expense_group_id__in=expense_group_ids).all()

        chain_tasks = []
        in_progress_expenses = []

        for index, expense_group in enumerate(expense_groups):

            error = errors.filter(workspace_id=workspace_id, expense_group=expense_group, is_resolved=False).first()
            skip_export = validate_failing_export(is_auto_export, interval_hours, error)
            if skip_export:
                logger.info('Skipping expense group %s as it has %s errors', expense_group.id, error.repetition_count)
                continue
            
            task_log, _ = TaskLog.objects.get_or_create(
                workspace_id=expense_group.workspace_id,
                expense_group=expense_group,
                defaults={
                    'status': 'ENQUEUED',
                    'type': 'CREATING_JOURNAL_ENTRY'
                }
            )

            if task_log.status not in ['IN_PROGRESS', 'ENQUEUED']:
                task_log.type = 'CREATING_JOURNAL_ENTRY'
                task_log.status = 'ENQUEUED'
                task_log.save()
            
            last_export = False
            if expense_groups.count() == index + 1:
                last_export = True

            chain_tasks.append({
                    'target': 'apps.netsuite.tasks.create_journal_entry',
                    'expense_group': expense_group,
                    'task_log_id': task_log.id,
                    'last_export': last_export
                    })

            if not (is_auto_export and expense_group.expenses.first().previous_export_state == 'ERROR'):
                in_progress_expenses.extend(expense_group.expenses.all())

        if len(chain_tasks) > 0:
                fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
                __create_chain_and_run(fyle_credentials, in_progress_expenses, workspace_id, chain_tasks, fund_source)
