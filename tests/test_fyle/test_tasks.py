import pytest
from fyle_integrations_platform_connector import PlatformConnector

from apps.fyle.models import ExpenseGroup, Expense, ExpenseGroupSettings
from apps.tasks.models import TaskLog
from apps.fyle.tasks import create_expense_groups, schedule_expense_group_creation
from apps.workspaces.models import Configuration, FyleCredential
from .fixtures import data


@pytest.mark.django_db()
def test_create_expense_group(mocker, add_fyle_credentials):

    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'IN_PROGRESS'
        }
    )
    
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=1)
    expense_group_settings.import_card_credits = True
    expense_group_settings.save()

    configuration = Configuration.objects.get(workspace_id=1)

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=data['expenses']
    )

    create_expense_groups(1, configuration, ['PERSONAL', 'CCC'], task_log)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1)
    expenses = Expense.objects.filter(org_id='orsO0VW86WLQ')
    
    assert len(expense_group) == 4
    assert len(expenses) == 2

    fyle_credential = FyleCredential.objects.get(workspace_id=1)
    fyle_credential.delete()

    create_expense_groups(1, configuration, ['PERSONAL', 'CCC'], task_log)

    task_log = TaskLog.objects.get(workspace_id=1)
    assert task_log.detail['message'] == 'Fyle credentials do not exist in workspace'
    assert task_log.status == 'FAILED'

    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=1)
    expense_group_settings.delete()

    create_expense_groups(1, configuration, ['PERSONAL', 'CCC'], task_log)

    task_log = TaskLog.objects.get(workspace_id=1)
    assert task_log.status == 'FATAL' 
    

@pytest.mark.django_db()
def test_schedule_expense_group_creation(mocker, add_fyle_credentials):

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=data['expenses']
    )
    schedule_expense_group_creation(workspace_id=1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1)
    expenses = Expense.objects.filter(org_id='or79Cob97KSh')

    assert len(expense_group) == 2
    assert len(expenses) == 2
