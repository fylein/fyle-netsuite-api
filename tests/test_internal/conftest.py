import pytest
from datetime import datetime, timezone

from apps.fyle.models import Expense, ExpenseGroup
from apps.workspaces.models import Workspace


@pytest.fixture
def create_workspace_for_stuck_export(db):
    workspace, _ = Workspace.objects.update_or_create(
        id=100,
        defaults={
            'name': 'Production Workspace',
            'fyle_org_id': 'or_stuck_test',
            'ns_account_id': 'test_account',
        }
    )
    return workspace


@pytest.fixture
def create_test_workspace(db):
    workspace, _ = Workspace.objects.update_or_create(
        id=101,
        defaults={
            'name': 'Fyle For Demo Test',
            'fyle_org_id': 'or_test_workspace',
            'ns_account_id': 'test_account',
        }
    )
    return workspace


@pytest.fixture
def create_expense_group_with_expenses(db, create_workspace_for_stuck_export):
    workspace = create_workspace_for_stuck_export
    
    expense = Expense.objects.create(
        workspace_id=workspace.id,
        expense_id='tx_stuck_test_1',
        employee_email='test@fyle.in',
        employee_name='Test Employee',
        category='Meals',
        sub_category='Team Meals',
        project='Test Project',
        expense_number='E/2024/01/T/1',
        claim_number='C/2024/01/R/1',
        amount=100.0,
        currency='USD',
        foreign_amount=100.0,
        foreign_currency='USD',
        settlement_id='setl_stuck_1',
        reimbursable=True,
        billable=False,
        state='APPROVED',
        vendor='Test Vendor',
        cost_center='Test Cost Center',
        purpose='Test expense',
        report_id='rp_stuck_report_1',
        report_title='Stuck Test Report',
        spent_at=datetime.now(tz=timezone.utc),
        approved_at=datetime.now(tz=timezone.utc),
        expense_created_at=datetime.now(tz=timezone.utc),
        expense_updated_at=datetime.now(tz=timezone.utc),
        fund_source='PERSONAL',
        verified_at=datetime.now(tz=timezone.utc),
        custom_properties={},
        org_id=workspace.fyle_org_id,
        file_ids=[],
        accounting_export_summary={}
    )
    
    expense_group = ExpenseGroup.objects.create(
        workspace_id=workspace.id,
        fund_source='PERSONAL',
        exported_at=None,
        description={
            'report_id': 'rp_stuck_report_1',
            'employee_email': 'test@fyle.in',
        }
    )
    expense_group.expenses.add(expense)
    
    return expense_group


@pytest.fixture
def create_stuck_task_log(db, create_workspace_for_stuck_export, create_expense_group_with_expenses):
    workspace = create_workspace_for_stuck_export
    expense_group = create_expense_group_with_expenses
    
    stuck_time = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
    task_log = TaskLog.objects.create(
        workspace_id=workspace.id,
        expense_group_id=expense_group.id,
        type='CREATING_BILL',
        status='ENQUEUED',
        stuck_export_re_attempt_count=0
    )
    TaskLog.objects.filter(id=task_log.id).update(updated_at=stuck_time)
    task_log.refresh_from_db()
    
    return task_log
