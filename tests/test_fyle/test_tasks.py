import pytest
from apps.fyle.models import ExpenseGroup, Expense
from apps.tasks.models import TaskLog
from apps.fyle.tasks import create_expense_groups, schedule_expense_group_creation
from apps.workspaces.models import Configuration
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

    configuration = Configuration.objects.get(workspace_id=1)

    mocker.patch(
        'apps.fyle.connector.FyleConnector.get_expenses',
        return_value=data['expenses']
    )

    create_expense_groups(1, configuration, ['PERSONAL', 'CCC'], task_log)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1)
    expenses = Expense.objects.filter(org_id='or79Cob97KSh')
    
    assert len(expense_group) == 2
    assert len(expenses) == 2

@pytest.mark.django_db()
def test_schedule_expense_group_creation(mocker, add_fyle_credentials):
    mocker.patch(
        'apps.fyle.connector.FyleConnector.get_expenses',
        return_value=data['expenses']
    )
    schedule_expense_group_creation(workspace_id=1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1)
    expenses = Expense.objects.filter(org_id='or79Cob97KSh')

    assert len(expense_group) == 2
    assert len(expenses) == 2
