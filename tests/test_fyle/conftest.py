from datetime import datetime, timezone
import pytest
from apps.fyle.models import ExpenseGroupSettings
from apps.workspaces.models import Workspace
from fyle_netsuite_api.tests import settings
from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog


@pytest.fixture
def create_temp_workspace(db):

    Workspace.objects.create(
        id=3,
        name='Fyle For Testing',
        fyle_org_id='riseabovehate',
        ns_account_id=settings.NS_ACCOUNT_ID,
        last_synced_at=None,
        source_synced_at=None,
        destination_synced_at=None,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc)
    )
    
    ExpenseGroupSettings.objects.create(
        reimbursable_expense_group_fields='{employee_email,report_id,claim_number,fund_source}',
        corporate_credit_card_expense_group_fields='{fund_source,employee_email,claim_number,expense_id,report_id}',
        expense_state='PAID',
        workspace_id=3,
        import_card_credits=False
    )


@pytest.fixture
def update_config_for_split_expense_grouping(db):
    def _update_config_for_split_expense_grouping(general_settings, expense_group_settings):
        general_settings.corporate_credit_card_expenses_object = 'CREDIT CARD CHARGE'
        general_settings.save()
        expense_group_settings.split_expense_grouping = 'SINGLE_LINE_ITEM'
        expense_group_settings.corporate_credit_card_expense_group_fields = [
            'expense_id',
            'claim_number',
            'fund_source',
            'employee_email',
            'report_id',
            'spent_at',
            'report_id'
        ]
        expense_group_settings.save()
    return _update_config_for_split_expense_grouping


@pytest.fixture
def setup_expense_groups_for_deletion_test(db):
    """
    Create expense groups and task logs for deletion test
    Use workspace_id=2 to avoid conflicts with other tests that use workspace_id=1
    """

    workspace_id = 2

    # Create expense groups for testing
    expense_group_1 = ExpenseGroup.objects.create(
        id=201,
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        employee_name='Test Employee 1'
    )

    expense_group_2 = ExpenseGroup.objects.create(
        id=202,
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        employee_name='Test Employee 2'
    )

    expense_group_3 = ExpenseGroup.objects.create(
        id=203,
        workspace_id=workspace_id,
        fund_source='CCC',
        employee_name='Test Employee 3'
    )

    # Create task logs that should be excluded from deletion
    reimbursement_task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='CREATING_REIMBURSEMENT',
        expense_group_id=expense_group_2.id,
        status='FAILED'
    )

    ap_payment_task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='CREATING_AP_PAYMENT',
        expense_group_id=expense_group_3.id,
        status='FAILED'
    )

    # Create a task log that should be deleted
    regular_task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='CREATING_JOURNAL_ENTRY',
        expense_group_id=expense_group_1.id,
        status='FAILED'
    )

    return {
        'expense_group_1': expense_group_1,
        'expense_group_2': expense_group_2, 
        'expense_group_3': expense_group_3,
        'reimbursement_task_log': reimbursement_task_log,
        'ap_payment_task_log': ap_payment_task_log,
        'regular_task_log': regular_task_log,
        'workspace_id': workspace_id
    }
