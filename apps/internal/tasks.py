import logging
from datetime import datetime, timedelta

from django.db.models import Q
from django_q.models import OrmQ

# from apps.fyle.actions import update_failed_expenses
from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog
from apps.workspaces.models import Workspace

# from django_q.tasks import async_task


logger = logging.getLogger(__name__)
logger.level = logging.INFO


def re_export_stuck_exports():
    prod_workspace_ids = Workspace.objects.filter(
        ~Q(name__icontains='fyle for') & ~Q(name__icontains='test')
    ).values_list('id', flat=True)
    task_logs = TaskLog.objects.filter(
        status__in=['ENQUEUED', 'IN_PROGRESS'],
        updated_at__lt=datetime.now() - timedelta(minutes=60),
        expense_group_id__isnull=False,
        workspace_id__in=prod_workspace_ids
    )
    if task_logs.count() > 0:
        logger.info('Re-exporting stuck task_logs')
        logger.info('%s stuck task_logs found', task_logs.count())
        # workspace_ids = task_logs.values_list('workspace_id', flat=True).distinct()
        expense_group_ids = task_logs.values_list('expense_group', flat=True)
        ormqs = OrmQ.objects.all()
        for orm in ormqs:
            if 'chain' in orm.task and orm.task['chain']:
                for chain in orm.task['chain']:
                    if len(chain) > 1 and isinstance(chain[1], list) and isinstance(chain[1][0], ExpenseGroup):
                        if chain[1][0].id in expense_group_ids:
                            logger.info('Skipping Re Export For Expense group %s', chain[1][0].id)
                            expense_group_ids.remove(chain[1][0].id)

        logger.info('Re-exporting Expense Group IDs: %s', expense_group_ids)
        # expense_groups = ExpenseGroup.objects.filter(id__in=expense_group_ids)
        # expenses = []
        # for expense_group in expense_groups:
        #     expenses.extend(expense_group.expenses.all())
        # workspace_ids_list = list(workspace_ids)
        # task_logs.update(status='FAILED', updated_at=datetime.now())
        # update_failed_expenses(expenses, True)
        # workspaces = Workspace.objects.filter(id__in=workspace_ids_list)
        # schedules = Schedule.objects.filter(
        #     args__in=[str(workspace.id) for workspace in workspaces],
        #     func='apps.workspaces.tasks.run_sync_schedule'
        # )
        # for workspace in workspaces:
        #     logger.info('Checking if 1hour sync schedule for workspace %s', workspace.id)
        #     schedule = schedules.filter(args=str(workspace.id)).first()
        #     # If schedule exist and it's within 1 hour, need not trigger it immediately
        #     if not (schedule and schedule.next_run < datetime.now(tz=schedule.next_run.tzinfo) + timedelta(minutes=60)):
        #         logger.info('Re-triggering sync schedule since no 1 hour schedule for workspace  %s', workspace.id)
        #         async_task('apps.workspaces.tasks.run_sync_schedule', workspace.id)
