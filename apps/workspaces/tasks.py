from datetime import datetime

from django_q.models import Schedule

from apps.fyle.models import ExpenseGroup
from apps.fyle.tasks import async_create_expense_groups
from apps.netsuite.tasks import schedule_bills_creation, schedule_journal_entry_creation, \
    schedule_expense_reports_creation
from apps.tasks.models import TaskLog
from apps.workspaces.models import WorkspaceSchedule, WorkspaceGeneralSettings


def schedule_sync(workspace_id: int, schedule_enabled: bool, hours: int):
    ws_schedule, _ = WorkspaceSchedule.objects.get_or_create(
        workspace_id=workspace_id
    )

    if schedule_enabled:
        ws_schedule.enabled = schedule_enabled
        ws_schedule.start_datetime = datetime.now()
        ws_schedule.interval_hours = hours

        schedule, _ = Schedule.objects.update_or_create(
            func='apps.workspaces.tasks.run_sync_schedule',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': hours * 60,
                'next_run': datetime.now()
            }
        )

        ws_schedule.schedule = schedule

        ws_schedule.save()

    elif not schedule_enabled:
        schedule = ws_schedule.schedule
        ws_schedule.enabled = schedule_enabled
        ws_schedule.schedule = None
        ws_schedule.save()
        schedule.delete()

    return ws_schedule


def run_sync_schedule(workspace_id):
    """
    Run schedule
    :param user: user email
    :param workspace_id: workspace id
    :return: None
    """
    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=workspace_id,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'IN_PROGRESS'
        }
    )

    general_settings = WorkspaceGeneralSettings.objects.get(workspace_id=workspace_id)

    fund_source = ['PERSONAL']
    if general_settings.corporate_credit_card_expenses_object:
        fund_source.append('CCC')
    if general_settings.reimbursable_expenses_object:
        async_create_expense_groups(
            workspace_id=workspace_id, fund_source=fund_source, task_log=task_log
        )

    if task_log.status == 'COMPLETE':

        if general_settings.reimbursable_expenses_object:

            expense_group_ids = ExpenseGroup.objects.filter(fund_source='PERSONAL',
                                                            workspace_id=workspace_id).values_list('id', flat=True)

            if general_settings.reimbursable_expenses_object == 'BILL':
                schedule_bills_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

            elif general_settings.reimbursable_expenses_object == 'EXPENSE REPORT':
                schedule_expense_reports_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

            elif general_settings.reimbursable_expenses_object == 'JOURNAL ENTRY':
                schedule_journal_entry_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

        if general_settings.corporate_credit_card_expenses_object:
            expense_group_ids = ExpenseGroup.objects.filter(fund_source='CCC',
                                                            workspace_id=workspace_id).values_list('id', flat=True)

            if general_settings.corporate_credit_card_expenses_object == 'JOURNAL ENTRY':
                schedule_journal_entry_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

            elif general_settings.corporate_credit_card_expenses_object == 'BILL':
                schedule_bills_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

            elif general_settings.corporate_credit_card_expenses_object == 'EXPENSE REPORT':
                schedule_expense_reports_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )
