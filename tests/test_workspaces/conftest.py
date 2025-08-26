from apps.fyle.models import ExpenseGroupSettings, ExpenseGroup
from apps.workspaces.models import LastExportDetail, Workspace
from apps.tasks.models import TaskLog, Error
from fyle_accounting_mappings.models import ExpenseAttribute
import pytest
from apps.users.models import User

@pytest.fixture
def create_task_logs(access_token):
    TaskLog.objects.update_or_create(
        workspace_id=49,
        type='CREATING_EXPENSE_REPORT',
        defaults={
            'status': 'FAILED'
        }
    )


@pytest.fixture()
def add_workspace_with_settings(db):
    """
    Add workspace with all required settings for export settings tests
    """
    def _create_workspace(workspace_id: int) -> int:
        Workspace.objects.update_or_create(
            id=workspace_id,
            defaults={
                'name': f'Test Workspace {workspace_id}',
                'fyle_org_id': f'fyle_org_{workspace_id}'
            }
        )
        LastExportDetail.objects.update_or_create(workspace_id=workspace_id)

        ExpenseGroupSettings.objects.update_or_create(
            workspace_id=workspace_id,
            defaults={
                'reimbursable_expense_group_fields': ['employee_email', 'report_id', 'claim_number', 'fund_source'],
                'corporate_credit_card_expense_group_fields': ['fund_source', 'employee_email', 'claim_number', 'expense_id', 'report_id'],
                'expense_state': 'PAYMENT_PROCESSING',
                'reimbursable_export_date_type': 'current_date',
                'ccc_export_date_type': 'current_date'
            }
        )
        return workspace_id

    return _create_workspace


@pytest.fixture()
def create_test_expense_groups_and_errors(db):
    """
    Create test expense groups and errors for export settings tests
    """
    def _create_test_data(workspace_id: int):
        personal_expense_group = ExpenseGroup.objects.create(
            id=201,
            workspace_id=workspace_id,
            fund_source='PERSONAL',
            exported_at=None
        )

        ccc_expense_group = ExpenseGroup.objects.create(
            id=202,
            workspace_id=workspace_id,
            fund_source='CCC',
            exported_at=None
        )

        employee_attr = ExpenseAttribute.objects.create(
            workspace_id=workspace_id,
            attribute_type='EMPLOYEE',
            display_name='Employee',
            value='test.employee2@example.com'
        )

        mapping_error = Error.objects.create(
            workspace_id=workspace_id,
            type='EMPLOYEE_MAPPING',
            expense_attribute=employee_attr,
            mapping_error_expense_group_ids=[201, 202],
            error_title='test.employee@example.com',
            error_detail='Employee mapping is missing',
            is_resolved=False
        )

        direct_error = Error.objects.create(
            workspace_id=workspace_id,
            type='INTACCT_ERROR',
            expense_group_id=201,
            error_title='Export failed',
            error_detail='Some export error'
        )

        failed_task_log = TaskLog.objects.create(
            workspace_id=workspace_id,
            expense_group_id=201,
            status='FAILED',
            type='CREATING_EXPENSE_REPORT'
        )

        return {
            'personal_expense_group': personal_expense_group,
            'ccc_expense_group': ccc_expense_group,
            'employee_attr': employee_attr,
            'mapping_error': mapping_error,
            'direct_error': direct_error,
            'failed_task_log': failed_task_log
        }

    return _create_test_data
