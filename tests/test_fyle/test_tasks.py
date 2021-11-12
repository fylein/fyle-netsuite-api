import pytest
from apps.fyle.models import ExpenseGroup, Expense
from apps.tasks.models import TaskLog
from apps.fyle.tasks import create_expense_groups

from .fixtures import data

@pytest.mark.django_db()
def test_create_expense_group(test_connection, create_expense_group_settings, mocker):

    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'IN_PROGRESS'
        }
    )

    mocker.patch(
        'apps.fyle.connector.FyleConnector.get_expenses',
        return_value=data['expenses']
    )

    create_expense_groups(1, ['PERSONAL', 'CCC'], task_log)

    expense_group = ExpenseGroup.objects.all()
    expenses = Expense.objects.all()
    
    assert len(expense_group) == 3
    assert len(expenses) == 6
