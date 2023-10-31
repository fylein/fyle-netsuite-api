import pytest
from apps.fyle.models import Expense, ExpenseGroup
from apps.tasks.models import TaskLog
from apps.workspaces.models import Configuration, WorkspaceSchedule
from apps.workspaces.tasks import *
from tests.test_fyle.fixtures import data as fyle_data

def test_schedule_sync(db):
    schedule_sync(2, True, 3, ['ashwin.t@fyle.in'], ['ashwin.t@fyle.in'])

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.interval_hours == 3
    assert ws_schedule.enabled == True

    schedule_sync(2, False, 0, ['ashwin.t@fyle.in'], ['ashwin.t@fyle.in'])

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.enabled == False

def test_run_sync_schedule(db, access_token, add_fyle_credentials, add_netsuite_credentials, mocker):
    expense_group_count = ExpenseGroup.objects.filter(workspace_id=1).count()
    expenses_count = Expense.objects.filter(org_id='or79Cob97KSh').count()

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=fyle_data['expenses']
    )
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
    assert expense_group == expense_group_count+2
    assert expenses == expenses_count+2

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
    
    run_email_notification(49)
    ws_schedule = WorkspaceSchedule.objects.get(
        workspace_id=49
    )
    assert ws_schedule.error_count == 1

    attribute = ExpenseAttribute.objects.filter(workspace_id=49, value='owner@fyleforintacct.in').first()
    attribute.delete()

    ws_schedule = WorkspaceSchedule.objects.get(workspace_id=49)
    ws_schedule.enabled = True
    ws_schedule.emails_selected = ['owner@fyleforintacct.in']
    ws_schedule.additional_email_options = [{'email': 'owner@fyleforintacct.in', 'name': 'Ashwin'}]
    ws_schedule.save()

    run_email_notification(49)

    ws_schedule = WorkspaceSchedule.objects.get(
        workspace_id=49
    )
    assert ws_schedule.enabled == True


@pytest.mark.django_db()
def test_async_update_workspace_name(mocker):
    mocker.patch(
        'apps.workspaces.tasks.get_fyle_admin',
        return_value={'data': {'org': {'name': 'Test Org'}}}
    )
    async_update_workspace_name(1, 'access_token')

    workspace = Workspace.objects.get(id=1)
    assert workspace.name == 'Test Org'
