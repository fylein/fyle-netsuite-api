import pytest

from apps.workspaces.models import Workspace, FyleCredential
from apps.fyle.tasks import create_expense_groups
from apps.tasks.models import TaskLog
from apps.fyle.models import ExpenseGroupSettings
from apps.fyle.helpers import check_interval_and_sync_dimension
from .fixtures import data

@pytest.fixture()
def create_expense_group_settings(test_connection, db):
    ExpenseGroupSettings.objects.update_or_create(
            workspace_id=1,
            defaults={
                'reimbursable_expense_group_fields': ['employee_email','report_id','claim_number','fund_source'],
                'corporate_credit_card_expense_group_fields': ['employee_email','report_id','claim_number','fund_source'],
                'expense_state':'PAYMENT_PROCESSING',
                'export_date_type': 'current_date'
            }
        )

@pytest.fixture()
def create_expense_group(test_connection, db, mocker):

    ExpenseGroupSettings.objects.update_or_create(
            workspace_id=1,
            defaults={
                'reimbursable_expense_group_fields': ['employee_email','report_id','claim_number','fund_source'],
                'corporate_credit_card_expense_group_fields': ['employee_email','report_id','claim_number','fund_source'],
                'expense_state':'PAYMENT_PROCESSING',
                'export_date_type': 'spent_at'
            }
        )

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

@pytest.fixture
def sync_fyle_dimensions():
    workspace = Workspace.objects.get(id=1)
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    check_interval_and_sync_dimension(workspace, fyle_credentials.refresh_token)