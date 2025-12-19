from datetime import datetime, timezone
import pytest
from apps.fyle.models import ExpenseGroupSettings, Expense
from apps.workspaces.models import Workspace, Configuration, LastExportDetail
from fyle_netsuite_api.tests import settings
from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog, Error
from fyle_accounting_mappings.models import ExpenseAttribute, CategoryMapping, DestinationAttribute


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
    
    LastExportDetail.objects.get_or_create(workspace_id=3)
    
    Configuration.objects.create(
        workspace_id=3,
        reimbursable_expenses_object='EXPENSE REPORT',
        corporate_credit_card_expenses_object='CREDIT CARD CHARGE'
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


@pytest.fixture
def add_category_test_expense(db, create_temp_workspace):
    workspace = Workspace.objects.get(id=3)
    expense = Expense.objects.create(
        workspace_id=workspace.id,
        expense_id='txCategoryTest',
        employee_email='category.test@test.com',
        employee_name='Category Test User',
        category='Test Category',
        amount=100,
        currency='USD',
        org_id=workspace.fyle_org_id,
        settlement_id='setlCat',
        report_id='rpCat',
        spent_at='2024-01-01T00:00:00Z',
        expense_created_at='2024-01-01T00:00:00Z',
        expense_updated_at='2024-01-01T00:00:00Z',
        fund_source='PERSONAL'
    )
    return expense


@pytest.fixture
def add_category_test_expense_group(db, add_category_test_expense):
    workspace = Workspace.objects.get(id=3)
    expense = add_category_test_expense
    expense_group = ExpenseGroup.objects.create(
        workspace_id=workspace.id,
        fund_source='PERSONAL',
        description={'employee_email': expense.employee_email},
        employee_name=expense.employee_name
    )
    expense_group.expenses.add(expense)
    return expense_group


@pytest.fixture
def add_category_mapping_error(db, add_category_test_expense_group):
    workspace = Workspace.objects.get(id=3)
    expense_group = add_category_test_expense_group
    error = Error.objects.create(
        workspace_id=workspace.id,
        type='CATEGORY_MAPPING',
        is_resolved=False,
        mapping_error_expense_group_ids=[expense_group.id]
    )
    return error


@pytest.fixture
def add_category_expense_attribute(db, create_temp_workspace):
    workspace = Workspace.objects.get(id=3)
    expense_attribute = ExpenseAttribute.objects.create(
        workspace_id=workspace.id,
        attribute_type='CATEGORY',
        value='Test Category Attribute',
        display_name='Category',
        source_id='catTest123'
    )
    return expense_attribute


@pytest.fixture
def add_mapped_category(db, create_temp_workspace):
    workspace = Workspace.objects.get(id=3)
    
    destination_account = DestinationAttribute.objects.create(
        workspace_id=workspace.id,
        attribute_type='ACCOUNT',
        display_name='Account',
        value='Expense Account',
        destination_id='acc123',
        active=True
    )
    
    destination_expense_head = DestinationAttribute.objects.create(
        workspace_id=workspace.id,
        attribute_type='EXPENSE_CATEGORY',
        display_name='Expense Category',
        value='Expense Category',
        destination_id='expcat123',
        active=True
    )
    
    expense_attribute = ExpenseAttribute.objects.create(
        workspace_id=workspace.id,
        attribute_type='CATEGORY',
        value='Mapped Category',
        display_name='Category',
        source_id='catMapped123',
        active=True
    )
    
    category_mapping = CategoryMapping.objects.create(
        workspace_id=workspace.id,
        source_category_id=expense_attribute.id,
        destination_account_id=destination_account.id,
        destination_expense_head_id=destination_expense_head.id
    )
    
    return category_mapping
