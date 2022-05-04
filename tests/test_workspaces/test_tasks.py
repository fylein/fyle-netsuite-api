import pytest
from apps.fyle.models import Expense, ExpenseGroup
from apps.netsuite.models import ExpenseReport
from apps.tasks.models import TaskLog

from apps.workspaces.models import WorkspaceSchedule
from apps.workspaces.tasks import run_sync_schedule, schedule_sync

def test_schedule_sync(db):
    schedule_sync(2, True, 3, [], [])

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.interval_hours == 3
    assert ws_schedule.enabled == True

    schedule_sync(2, False, 0, [], [])

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.enabled == False

def test_run_sync_schedule(db, test_connection, add_fyle_credentials, add_netsuite_credentials):
    run_sync_schedule(1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1)
    expenses = Expense.objects.filter(org_id='or79Cob97KSh')
    
    assert len(expense_group) == 2
    assert len(expenses) == 2

    run_sync_schedule(2)
    expense_group = ExpenseGroup.objects.filter(workspace_id=2)
    expenses = Expense.objects.filter(org_id='oraWFQlEpjbb')

    assert len(expense_group) == 2
    assert len(expenses) == 2


