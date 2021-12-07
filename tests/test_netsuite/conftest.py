import pytest
from apps.fyle.models import Expense, ExpenseGroup
from apps.tasks.models import TaskLog
from apps.netsuite.models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem

@pytest.fixture
def create_task_logs(db):
    TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

    TaskLog.objects.update_or_create(
        workspace_id=2,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

    TaskLog.objects.update_or_create(
        workspace_id=49,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

@pytest.fixture
def create_expense_report(db, add_netsuite_credentials, add_fyle_credentials):

    TaskLog.objects.update_or_create(
        workspace_id=2,
        expense_group_id=1,
        type='FETCHING_EXPENSES',
        detail={
          'internalId': 10913
        },
        defaults={
            'status': 'COMPLETE'
        }
    )

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    ExpenseReport.create_expense_report(expense_group)
    ExpenseReportLineItem.create_expense_report_lineitems(expense_group)
