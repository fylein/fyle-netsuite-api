from fyle_accounting_mappings.models import ExpenseAttribute

from apps.fyle.models import ExpenseGroup
from apps.tasks.models import Error, TaskLog
from apps.workspaces.models import Configuration
from apps.workspaces.apis.export_settings.helpers import clear_workspace_errors_on_export_type_change


def test_clear_workspace_errors_no_changes(add_workspace_with_settings):
    """
    Test when no export settings change - uses existing workspace data
    """
    workspace_id = 1
    add_workspace_with_settings(workspace_id)

    old_config = {
        'reimbursable_expenses_object': 'EXPENSE_REPORT',
        'corporate_credit_card_expenses_object': 'CHARGE_CARD_TRANSACTION'
    }

    new_config, _ = Configuration.objects.update_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': 'EXPENSE_REPORT',
            'corporate_credit_card_expenses_object': 'CHARGE_CARD_TRANSACTION'
        }
    )
    TaskLog.objects.create(
        workspace_id=workspace_id,
        status='ENQUEUED',
        type='CREATING_EXPENSE_REPORT'
    )

    clear_workspace_errors_on_export_type_change(
        workspace_id, old_config, new_config
    )

    enqueued_exists = TaskLog.objects.filter(
        workspace_id=workspace_id,
        status='ENQUEUED',
        type='CREATING_EXPENSE_REPORT'
    ).exists()
    assert enqueued_exists is True


def test_clear_workspace_errors_with_mapping_errors(add_workspace_with_settings):
    """
    Test mapping error handling when reimbursable expenses object changes
    """
    workspace_id = 2
    add_workspace_with_settings(workspace_id)

    _ = ExpenseGroup.objects.create(
        id=201,
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    _ = ExpenseGroup.objects.create(
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
        error_detail='Employee mapping is missing'
    )

    direct_error = Error.objects.create(
        workspace_id=workspace_id,
        type='INTACCT_ERROR',
        expense_group_id=201,
        error_title='Export failed',
        error_detail='Some export error'
    )

    TaskLog.objects.create(
        workspace_id=workspace_id,
        expense_group_id=201,
        status='FAILED',
        type='CREATING_EXPENSE_REPORT'
    )

    old_config = {
        'reimbursable_expenses_object': 'EXPENSE_REPORT',
        'corporate_credit_card_expenses_object': 'CHARGE_CARD_TRANSACTION'
    }

    new_config, _ = Configuration.objects.get_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': 'BILL',
            'corporate_credit_card_expenses_object': 'CHARGE_CARD_TRANSACTION'
        }
    )

    clear_workspace_errors_on_export_type_change(
        workspace_id, old_config, new_config
    )

    mapping_error.refresh_from_db()
    assert mapping_error.mapping_error_expense_group_ids == [202]

    direct_error_exists = Error.objects.filter(id=direct_error.id).exists()
    assert direct_error_exists is False

    task_log_exists = TaskLog.objects.filter(
        workspace_id=workspace_id,
        expense_group_id=201,
        status='FAILED'
    ).exists()
    assert task_log_exists is False


def test_clear_workspace_errors_enqueued_tasks_deleted_on_change(add_workspace_with_settings):
    """
    Test that ENQUEUED task logs are deleted when export settings change
    """
    workspace_id = 3
    add_workspace_with_settings(workspace_id)

    ExpenseGroup.objects.create(
        id=501,
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    TaskLog.objects.create(
        workspace_id=workspace_id,
        status='ENQUEUED',
        type='CREATING_EXPENSE_REPORT'
    )

    TaskLog.objects.create(
        workspace_id=workspace_id,
        status='ENQUEUED',
        type='CREATING_BILL'
    )

    TaskLog.objects.create(
        workspace_id=workspace_id,
        status='ENQUEUED',
        type='FETCHING_EXPENSES'
    )

    old_config = {
        'reimbursable_expenses_object': 'EXPENSE_REPORT',
        'corporate_credit_card_expenses_object': 'CHARGE_CARD_TRANSACTION'
    }

    new_config, _ = Configuration.objects.get_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': 'BILL',
            'corporate_credit_card_expenses_object': 'CHARGE_CARD_TRANSACTION'
        }
    )

    clear_workspace_errors_on_export_type_change(
        workspace_id, old_config, new_config
    )

    enqueued_count = TaskLog.objects.filter(
        workspace_id=workspace_id,
        status='ENQUEUED'
    ).exclude(type__in=['FETCHING_EXPENSES', 'CREATING_BILL_PAYMENT']).count()
    assert enqueued_count == 0

    excluded_exists = TaskLog.objects.filter(
        workspace_id=workspace_id,
        status='ENQUEUED',
        type='FETCHING_EXPENSES'
    ).exists()
    assert excluded_exists is True


def test_clear_workspace_errors_complete_mapping_deletion(add_workspace_with_settings):
    """
    Test when mapping error should be completely deleted (no remaining expense groups)
    """
    workspace_id = 4
    add_workspace_with_settings(workspace_id)

    _ = ExpenseGroup.objects.create(
        id=301,
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    category_attr = ExpenseAttribute.objects.create(
        workspace_id=workspace_id,
        attribute_type='CATEGORY',
        display_name='Category',
        value='Travel-Test'
    )

    mapping_error = Error.objects.create(
        workspace_id=workspace_id,
        type='CATEGORY_MAPPING',
        expense_attribute=category_attr,
        mapping_error_expense_group_ids=[301],
        error_title='Travel',
        error_detail='Category mapping is missing'
    )

    old_config = {
        'reimbursable_expenses_object': 'EXPENSE_REPORT',
        'corporate_credit_card_expenses_object': 'CHARGE_CARD_TRANSACTION'
    }

    new_config, _ = Configuration.objects.get_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': 'BILL',
            'corporate_credit_card_expenses_object': 'CHARGE_CARD_TRANSACTION'
        }
    )

    clear_workspace_errors_on_export_type_change(
        workspace_id, old_config, new_config
    )

    mapping_error_exists = Error.objects.filter(id=mapping_error.id).exists()
    assert mapping_error_exists is False
