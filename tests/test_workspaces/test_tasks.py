import pytest
from apps.fyle.models import Expense, ExpenseGroup
from apps.netsuite.models import ExpenseReport
from apps.tasks.models import TaskLog

from apps.workspaces.models import Configuration, WorkspaceSchedule
from apps.workspaces.tasks import run_sync_schedule, schedule_sync, delete_cards_mapping_settings, run_email_notification

def test_schedule_sync(db):
    schedule_sync(2, True, 3, [], [])

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.interval_hours == 3
    assert ws_schedule.enabled == True

    schedule_sync(2, False, 0, [], [])

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.enabled == False

def test_run_sync_schedule(db, access_token, add_fyle_credentials, add_netsuite_credentials):
    run_sync_schedule(1)

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.reimbursable_expenses_object = 'BILL'
    configuration.save()
    run_sync_schedule(1)

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.reimbursable_expenses_object = 'JOURNAL ENTRY'
    configuration.save()
    run_sync_schedule(1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).count()
    expenses = Expense.objects.filter(org_id='or79Cob97KSh').count()
    assert expense_group == 2
    assert expenses == 2

    run_sync_schedule(2)

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.corporate_credit_card_expenses_object = 'JOURNAL ENTRY'
    configuration.save()
    run_sync_schedule(2)

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.corporate_credit_card_expenses_object = 'EXPENSE REPORT'
    configuration.save()
    run_sync_schedule(2)

    expense_group = ExpenseGroup.objects.filter(workspace_id=2).count()
    expenses = Expense.objects.filter(org_id='oraWFQlEpjbb').count()

    assert expense_group == 2
    assert expenses == 2


@pytest.mark.django_db()
def test_delete_cards_mapping_settings():
    configuration = Configuration.objects.get(workspace_id=49)
    configuration.map_fyle_cards_netsuite_account = False
    configuration.save()
    delete_cards_mapping_settings(configuration)


@pytest.mark.django_db()
def test_run_email_notification(db, mocker, create_task_logs):
    tasks = TaskLog.objects.filter(workspace_id = 49)
    
    run_email_notification(49)
    ws_schedule = WorkspaceSchedule.objects.get(
        workspace_id=49
    )
    assert ws_schedule.error_count == 1
    