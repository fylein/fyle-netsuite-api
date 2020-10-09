from datetime import datetime

from django.conf import settings

from apps.fyle.models import ExpenseGroup
from apps.fyle.tasks import create_expense_groups
from apps.fyle.utils import FyleConnector
from apps.netsuite.tasks import schedule_bills_creation, schedule_journal_entry_creation, \
    schedule_expense_reports_creation
from apps.tasks.models import TaskLog
from apps.workspaces.models import WorkspaceSchedule, FyleCredential, WorkspaceGeneralSettings


def schedule_sync(workspace_id: int, schedule_enabled: bool, hours: int, next_run: str, user: str):
    ws_schedule, _ = WorkspaceSchedule.objects.get_or_create(
        workspace_id=workspace_id
    )
    start_datetime = datetime.strptime(next_run, '%Y-%m-%dT%H:%M:%S.%fZ')

    if schedule_enabled:
        ws_schedule.enabled = schedule_enabled
        ws_schedule.start_datetime = start_datetime
        ws_schedule.interval_hours = hours

        created_job = create_schedule_job(
            workspace_id=workspace_id,
            schedule=ws_schedule,
            user=user,
            start_datetime=start_datetime,
            hours=hours
        )
        ws_schedule.fyle_job_id = created_job['id']

        ws_schedule.save(update_fields=['enabled', 'start_datetime', 'interval_hours', 'fyle_job_id'])

    elif not schedule_enabled:
        fyle_credentials = FyleCredential.objects.get(
            workspace_id=workspace_id)
        fyle_connector = FyleConnector(fyle_credentials.refresh_token, workspace_id)
        fyle_sdk_connection = fyle_connector.connection

        jobs = fyle_sdk_connection.Jobs
        if ws_schedule.fyle_job_id:
            jobs.delete(ws_schedule.fyle_job_id)

        ws_schedule.fyle_job_id = None
        ws_schedule.enabled = False

        ws_schedule.save(update_fields=['enabled', 'fyle_job_id'])

    return ws_schedule


def create_schedule_job(workspace_id: int, schedule: WorkspaceSchedule, user: str,
                        start_datetime: datetime, hours: int):
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, workspace_id)
    fyle_sdk_connection = fyle_connector.connection

    jobs = fyle_sdk_connection.Jobs
    user_profile = fyle_sdk_connection.Employees.get_my_profile()['data']

    created_job = jobs.trigger_interval(
        callback_url='{0}{1}'.format(
            settings.API_URL,
            '/workspaces/{0}/schedule/trigger/'.format(workspace_id)
        ),
        callback_method='POST',
        object_id=schedule.id,
        job_description='Fetch expenses: Workspace id - {0}, user - {1}'.format(
            workspace_id, user
        ),
        start_datetime=start_datetime.strftime('%Y-%m-%d %H:%M:00.00'),
        hours=hours,
        org_user_id=user_profile['id'],
        payload={}
    )
    return created_job


def run_sync_schedule(workspace_id, user: str):
    """
    Run schedule
    :param user: user email
    :param workspace_id: workspace id
    :return: None
    """
    task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='FETCHING_EXPENSES',
        status='IN_PROGRESS'
    )

    general_settings = WorkspaceGeneralSettings.objects.get(workspace_id=workspace_id)

    fund_source = ['PERSONAL']
    if general_settings.corporate_credit_card_expenses_object:
        fund_source.append('CCC')
    if general_settings.reimbursable_expenses_object:
        task_log: TaskLog = create_expense_groups(
            workspace_id=workspace_id, fund_source=fund_source, task_log=task_log
        )

    if task_log.status == 'COMPLETE':

        if general_settings.reimbursable_expenses_object:

            expense_group_ids = ExpenseGroup.objects.filter(fund_source='PERSONAL').values_list('id', flat=True)

            if general_settings.reimbursable_expenses_object == 'VENDOR BILL':
                schedule_bills_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids, user=user
                )

            elif general_settings.reimbursable_expenses_object == 'EXPENSE REPORT':
                schedule_expense_reports_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids, user=user
                )

            elif general_settings.reimbursable_expenses_object == 'JOURNAL ENTRY':
                schedule_journal_entry_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids, user=user
                )

        if general_settings.corporate_credit_card_expenses_object:
            expense_group_ids = ExpenseGroup.objects.filter(fund_source='CCC').values_list('id', flat=True)

            if general_settings.corporate_credit_card_expenses_object == 'JOURNAL ENTRY':
                schedule_journal_entry_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids, user=user
                )

            elif general_settings.corporate_credit_card_expenses_object == 'VENDOR BILL':
                schedule_bills_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids, user=user
                )

            elif general_settings.corporate_credit_card_expenses_object == 'EXPENSE REPORT':
                schedule_expense_reports_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids, user=user
                )
