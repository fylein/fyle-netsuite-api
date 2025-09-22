import hashlib
import pytest
import json
from django.db.models import Q
from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum
from django_q.models import Schedule

from apps.fyle.models import ExpenseGroup, Expense, ExpenseGroupSettings
from apps.tasks.models import TaskLog, Error
from apps.fyle.actions import post_accounting_export_summary
from apps.fyle.tasks import (
    create_expense_groups,
    import_and_export_expenses,
    schedule_expense_group_creation,
    skip_expenses_and_post_accounting_export_summary,
    update_non_exported_expenses,
    handle_fund_source_changes_for_expense_ids,
    process_expense_group_for_fund_source_update,
    delete_expense_group_and_related_data,
    recreate_expense_groups,
    schedule_task_for_expense_group_fund_source_change,
    cleanup_scheduled_task
)
from apps.workspaces.models import Configuration, FyleCredential, Workspace
from .fixtures import data
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework import status
from tests.helper import dict_compare_keys
from unittest import mock
from apps.fyle.actions import mark_expenses_as_skipped
from fyle.platform.exceptions import InvalidTokenError, InternalServerError
from apps.fyle.models import ExpenseFilter
from apps.fyle.tasks import group_expenses_and_save


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

    with mock.patch('fyle_integrations_platform_connector.apis.Expenses.get') as mock_call:
        mock_call.side_effect = [
            data['expenses'],
            []
        ]
        expense_group_count = len(ExpenseGroup.objects.filter(workspace_id=1))
        expenses_count = len(Expense.objects.filter(org_id='or79Cob97KSh'))

        create_expense_groups(1, ['PERSONAL', 'CCC'], task_log, ExpenseImportSourceEnum.DASHBOARD_SYNC)

        expense_group = ExpenseGroup.objects.filter(workspace_id=1)
        expenses = Expense.objects.filter(org_id='or79Cob97KSh')
        
        assert len(expense_group) == expense_group_count+2
        assert len(expenses) == expenses_count+2

        fyle_credential = FyleCredential.objects.get(workspace_id=1)
        fyle_credential.delete()

        create_expense_groups(1, ['PERSONAL', 'CCC'], task_log, ExpenseImportSourceEnum.DASHBOARD_SYNC)

        task_log = TaskLog.objects.get(workspace_id=1)
        assert task_log.detail['message'] == 'Fyle credentials do not exist in workspace'
        assert task_log.status == 'FAILED'

        expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=1)
        expense_group_settings.delete()

        create_expense_groups(1, ['PERSONAL', 'CCC'], task_log, ExpenseImportSourceEnum.DASHBOARD_SYNC)

        task_log = TaskLog.objects.get(workspace_id=1)
        assert task_log.status == 'FATAL'

        mock_call.side_effect = InternalServerError('Error')
        create_expense_groups(1, ['PERSONAL', 'CCC'], task_log, ExpenseImportSourceEnum.DASHBOARD_SYNC)

        mock_call.side_effect = InvalidTokenError('Invalid Token')
        create_expense_groups(1, ['PERSONAL', 'CCC'], task_log, ExpenseImportSourceEnum.DASHBOARD_SYNC)

        assert mock_call.call_count == 2


@pytest.mark.django_db()
def test_create_expense_group_skipped_flow(mocker, api_client, add_fyle_credentials, access_token):
    #adding the expense-filter
    url = reverse('expense-filters', 
        kwargs={
            'workspace_id': 1,
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.post(url,data=data['expense_filter_0'])
    assert response.status_code == 201
    response = json.loads(response.content)

    assert dict_compare_keys(response, data['expense_filter_0_response']) == [], 'expense group api return diffs in keys'

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

    with mock.patch('fyle_integrations_platform_connector.apis.Expenses.get') as mock_call:
        mock_call.side_effect = [
            data['expenses'],
            data['ccc_expenses']
        ]

        expense_group_count = len(ExpenseGroup.objects.filter(workspace_id=1))
        expenses_count = len(Expense.objects.filter(org_id='or79Cob97KSh'))

        create_expense_groups(1, ['PERSONAL', 'CCC'], task_log, ExpenseImportSourceEnum.DASHBOARD_SYNC)
        expense_group = ExpenseGroup.objects.filter(workspace_id=1)
        expenses = Expense.objects.filter(org_id='or79Cob97KSh')

        assert len(expense_group) == expense_group_count+2
        assert len(expenses) == expenses_count+4

        for expense in expenses:
            if expense.employee_email == 'jhonsnow@fyle.in': 
                assert expense.is_skipped == True


@pytest.mark.django_db()
def test_schedule_expense_group_creation(mocker, add_fyle_credentials):

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=data['expenses']
    )

    expense_group_count = len(ExpenseGroup.objects.filter(workspace_id=1))
    expenses_count = len(Expense.objects.filter(org_id='or79Cob97KSh'))

    schedule_expense_group_creation(workspace_id=1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1)
    expenses = Expense.objects.filter(org_id='or79Cob97KSh')

    #the count didn't increased beacause async blocks don't work while testing
    assert len(expense_group) == expense_group_count
    assert len(expenses) == expenses_count


def test_post_accounting_export_summary(db, mocker):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expense_id = expense_group.expenses.first().id
    expense_group.expenses.remove(expense_id)

    workspace = Workspace.objects.get(id=1)

    expense = Expense.objects.filter(id=expense_id).first()
    expense.workspace_id = 1
    expense.save()

    mark_expenses_as_skipped(Q(), [expense_id], workspace)

    assert Expense.objects.filter(id=expense_id).first().accounting_export_summary['synced'] == False

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.post_bulk_accounting_export_summary',
        return_value=[]
    )
    post_accounting_export_summary(1)

    assert Expense.objects.filter(id=expense_id).first().accounting_export_summary['synced'] == True


def test_update_non_exported_expenses(db, create_temp_workspace, mocker, api_client):
    expense = data['raw_expense']
    default_raw_expense = data['default_raw_expense']
    org_id = expense['org_id']
    payload = {
        "resource": "EXPENSE",
        "action": 'UPDATED_AFTER_APPROVAL',
        "data": expense,
        "reason": 'expense update testing',
    }

    expense_created, _ = Expense.objects.update_or_create(
        org_id=org_id,
        expense_id='txhJLOSKs1iN',
        workspace_id=1,
        defaults=default_raw_expense
    )
    expense_created.accounting_export_summary = {}
    expense_created.save()

    workspace = Workspace.objects.filter(id=1).first()
    workspace.fyle_org_id = org_id
    workspace.save()

    assert expense_created.category == 'Old Category'

    update_non_exported_expenses(payload['data'])

    expense = Expense.objects.get(expense_id='txhJLOSKs1iN', org_id=org_id)
    assert expense.category == 'ABN Withholding'

    expense.accounting_export_summary = {"synced": True, "state": "COMPLETE"}
    expense.category = 'Old Category'
    expense.save()

    update_non_exported_expenses(payload['data'])
    expense = Expense.objects.get(expense_id='txhJLOSKs1iN', org_id=org_id)
    assert expense.category == 'Old Category'

    try:
        update_non_exported_expenses(payload['data'])
    except ValidationError as e:
        assert e.detail[0] == 'Workspace mismatch'

    url = reverse('exports', kwargs={'workspace_id': 1})
    response = api_client.post(url, data=payload, format='json')
    assert response.status_code == status.HTTP_200_OK

    url = reverse('exports', kwargs={'workspace_id': 2})
    response = api_client.post(url, data=payload, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db()
def test_group_expenses_and_save(mocker, add_fyle_credentials):
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'IN_PROGRESS'
        }
    )
    workspace = Workspace.objects.get(id=1)

    # Get initial counts
    initial_expense_count = Expense.objects.filter(workspace_id=1).count()
    initial_expense_group_count = ExpenseGroup.objects.filter(workspace_id=1).count()

    # Test without expense filters
    group_expenses_and_save(test_expenses, task_log, workspace)
    
    # Verify expense objects were created
    expenses = Expense.objects.filter(workspace_id=1)
    assert expenses.count() == initial_expense_count + 2
    
    # Verify expense groups were created
    expense_groups = ExpenseGroup.objects.filter(workspace_id=1)
    assert expense_groups.count() == initial_expense_group_count + 2
    
    # Verify task log was updated
    task_log.refresh_from_db()
    assert task_log.status == 'COMPLETE'

    # Test with expense filters
    # Create an expense filter
    _ = ExpenseFilter.objects.create(
        workspace_id=1,
        condition='employee_email',
        operator='in',
        values=['test@fyle.in'],
        rank=1
    )
    # Run with filters
    group_expenses_and_save(test_expenses, task_log, workspace)

    # Verify that only one expense is not skipped (the one matching the filter)
    non_skipped_expenses = expenses.filter(is_skipped=False)
    assert non_skipped_expenses.count() == 1
    assert non_skipped_expenses.first().employee_email == 'test2@fyle.in'

    # Verify task log was updated
    task_log.refresh_from_db()
    assert task_log.status == 'COMPLETE'


def test_import_and_export_expenses_direct_export_case_1(mocker, db):
    """
    Test import and export expenses
    Case 1: Reimbursable expenses are not configured
    """
    workspace_id = 1
    workspace = Workspace.objects.get(id=workspace_id)
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    configuration.reimbursable_expenses_object = None
    configuration.save()

    mock_call = mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=data['expenses_webhook']
    )

    mock_skip_expenses_and_post_accounting_export_summary = mocker.patch(
        'apps.fyle.tasks.skip_expenses_and_post_accounting_export_summary',
        return_value=None
    )

    import_and_export_expenses(
        report_id='rp1s1L3QtMpF',
        org_id=workspace.fyle_org_id,
        is_state_change_event=False,
        imported_from=ExpenseImportSourceEnum.DIRECT_EXPORT
    )

    assert mock_call.call_count == 1
    assert mock_skip_expenses_and_post_accounting_export_summary.call_count == 1


def test_import_and_export_expenses_direct_export_case_2(mocker, db):
    """
    Test import and export expenses
    Case 2: Corporate credit card expenses are not configured
    """
    workspace_id = 1
    workspace = Workspace.objects.get(id=workspace_id)
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    configuration.corporate_credit_card_expenses_object = None
    configuration.save()

    expense_data = data['expenses_webhook'].copy()
    expense_data[0]['org_id'] = workspace.fyle_org_id
    expense_data[0]['source_account_type'] = 'PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT'

    mock_call = mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=expense_data
    )

    mock_skip_expenses_and_post_accounting_export_summary = mocker.patch(
        'apps.fyle.tasks.skip_expenses_and_post_accounting_export_summary',
        return_value=None
    )

    import_and_export_expenses(
        report_id='rp1s1L3QtMpF',
        org_id=workspace.fyle_org_id,
        is_state_change_event=False,
        imported_from=ExpenseImportSourceEnum.DIRECT_EXPORT
    )

    assert mock_call.call_count == 1
    assert mock_skip_expenses_and_post_accounting_export_summary.call_count == 1


def test_import_and_export_expenses_direct_export_case_3(mocker, db):
    """
    Test import and export expenses
    Case 3: Negative expesnes with filter_credit_expenses=True
    """
    workspace_id = 1
    workspace = Workspace.objects.get(id=workspace_id)
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    configuration.corporate_credit_card_expenses_object = None
    configuration.save()

    expense_data = data['expenses_webhook'].copy()
    expense_data[0]['org_id'] = workspace.fyle_org_id
    expense_data[0]['source_account_type'] = 'PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT'
    expense_data[0]['amount'] = -100

    mock_call = mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=expense_data
    )

    mock_skip_expenses_and_post_accounting_export_summary = mocker.patch(
        'apps.fyle.tasks.skip_expenses_and_post_accounting_export_summary',
        return_value=None
    )

    import_and_export_expenses(
        report_id='rp1s1L3QtMpF',
        org_id=workspace.fyle_org_id,
        is_state_change_event=False,
        imported_from=ExpenseImportSourceEnum.DIRECT_EXPORT
    )

    assert mock_call.call_count == 1
    assert mock_skip_expenses_and_post_accounting_export_summary.call_count == 1


def test_skip_expenses_and_post_accounting_export_summary(mocker, db):
    """
    Test skip expenses and post accounting export summary
    """
    workspace = Workspace.objects.get(id=1)

    expense = Expense.objects.filter(org_id='or79Cob97KSh').first()
    expense.workspace = workspace
    expense.org_id = workspace.fyle_org_id
    expense.accounting_export_summary = {}
    expense.is_skipped = False
    expense.fund_source = 'PERSONAL'
    expense.save()

    # Patch mark_expenses_as_skipped to return the expense in a list
    mock_mark_skipped = mocker.patch(
        'apps.fyle.tasks.mark_expenses_as_skipped',
        return_value=[expense]
    )
    # Patch post_accounting_export_summary to just record the call
    mock_post_summary = mocker.patch(
        'apps.fyle.tasks.post_accounting_export_summary',
        return_value=None
    )

    skip_expenses_and_post_accounting_export_summary([expense.id], workspace)

    # Assert mark_expenses_as_skipped was called with Q(), [expense.id], workspace
    assert mock_mark_skipped.call_count == 1
    args, _ = mock_mark_skipped.call_args
    assert args[1] == [expense.id]
    assert args[2] == workspace

    # Assert post_accounting_export_summary was called with workspace_id and expense_ids
    assert mock_post_summary.call_count == 1
    _, post_kwargs = mock_post_summary.call_args
    assert post_kwargs['workspace_id'] == workspace.id
    assert post_kwargs['expense_ids'] == [expense.id]


def test_handle_fund_source_changes_for_expense_ids(db, mocker, add_fyle_credentials):
    """
    Test handle fund source changes for expense ids
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Get count of expense groups before creating new ones
    initial_expense_group_count = ExpenseGroup.objects.filter(workspace_id=1).count()
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log, workspace)
    
    # Get only the newly created expense groups by filtering those created after the initial count
    all_expense_groups = ExpenseGroup.objects.filter(workspace_id=1).order_by('id')
    newly_created_expense_groups = all_expense_groups[initial_expense_group_count:]
    
    # Use the first newly created expense group and expense for our test
    expense_group = newly_created_expense_groups[0] if newly_created_expense_groups else all_expense_groups.first()
    expense = expense_group.expenses.first()
    workspace_id = 1
    
    changed_expense_ids = [expense.id]
    report_id = expense.report_id
    
    # Get all expenses from the newly created groups to include both PERSONAL and CCC
    new_expense_ids = []
    for group in newly_created_expense_groups:
        new_expense_ids.extend([e.id for e in group.expenses.all()])
    
    # If no new groups were created, fall back to all expenses
    if not new_expense_ids:
        all_expenses = Expense.objects.filter(workspace_id=workspace_id)
        personal_expense_ids = [e.id for e in all_expenses if e.fund_source == 'PERSONAL']
        ccc_expense_ids = [e.id for e in all_expenses if e.fund_source == 'CCC']
    else:
        all_new_expenses = Expense.objects.filter(id__in=new_expense_ids)
        personal_expense_ids = [e.id for e in all_new_expenses if e.fund_source == 'PERSONAL']
        ccc_expense_ids = [e.id for e in all_new_expenses if e.fund_source == 'CCC']

    mock_process_expense_group = mocker.patch(
        'apps.fyle.tasks.process_expense_group_for_fund_source_update',
        return_value=None
    )

    handle_fund_source_changes_for_expense_ids(
        workspace_id=workspace_id,
        changed_expense_ids=changed_expense_ids,
        report_id=report_id,
        affected_fund_source_expense_ids={'PERSONAL': personal_expense_ids, 'CCC': ccc_expense_ids},
        task_name='test_task'
    )

    assert mock_process_expense_group.call_count >= 1, f"Expected at least 1 call, got {mock_process_expense_group.call_count}"


def test_process_expense_group_enqueued_status(db, mocker, add_fyle_credentials):
    """
    Test process expense group when task log is ENQUEUED
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    workspace_id = 1
    changed_expense_ids = [expense_group.expenses.first().id]

    TaskLog.objects.filter(expense_group_id=expense_group.id).delete()

    task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='CREATING_JOURNAL_ENTRY',
        expense_group_id=expense_group.id,
        status='ENQUEUED'
    )

    mock_schedule = mocker.patch(
        'apps.fyle.tasks.schedule_task_for_expense_group_fund_source_change',
        return_value=None
    )

    process_expense_group_for_fund_source_update(
        expense_group=expense_group, 
        changed_expense_ids=changed_expense_ids, 
        workspace_id=workspace_id,
        report_id='rp1s1L3QtMpF',
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids}
    )
    task_log.delete()

    assert mock_schedule.call_count == 1


def test_process_expense_group_in_progress_status(db, mocker, add_fyle_credentials):
    """
    Test process expense group when task log is IN_PROGRESS
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    workspace_id = 1
    changed_expense_ids = [expense_group.expenses.first().id]

    TaskLog.objects.filter(expense_group_id=expense_group.id).delete()

    task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='CREATING_JOURNAL_ENTRY',
        expense_group_id=expense_group.id,
        status='IN_PROGRESS'
    )

    mock_schedule = mocker.patch(
        'apps.fyle.tasks.schedule_task_for_expense_group_fund_source_change',
        return_value=None
    )

    process_expense_group_for_fund_source_update(
        expense_group=expense_group, 
        changed_expense_ids=changed_expense_ids, 
        workspace_id=workspace_id,
        report_id='rp1s1L3QtMpF',
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids}
    )
    task_log.delete()

    assert mock_schedule.call_count == 1


def test_process_expense_group_complete_status(db, mocker, add_fyle_credentials):
    """
    Test process expense group when task log is COMPLETE
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    workspace_id = 1
    changed_expense_ids = [expense_group.expenses.first().id]

    TaskLog.objects.filter(expense_group_id=expense_group.id).delete()

    task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='CREATING_JOURNAL_ENTRY',
        expense_group_id=expense_group.id,
        status='COMPLETE'
    )

    mock_delete_recreate = mocker.patch(
        'apps.fyle.tasks.delete_expense_group_and_related_data',
        return_value=None
    )

    result = process_expense_group_for_fund_source_update(
        expense_group=expense_group, 
        changed_expense_ids=changed_expense_ids, 
        workspace_id=workspace_id,
        report_id='rp1s1L3QtMpF',
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids}
    )
    task_log.delete()

    assert mock_delete_recreate.call_count == 0
    assert result is False


def test_process_expense_group_no_task_log(db, mocker, add_fyle_credentials):
    """
    Test process expense group when no task log exists
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    workspace_id = 1
    changed_expense_ids = [expense_group.expenses.first().id]

    TaskLog.objects.filter(expense_group_id=expense_group.id).delete()

    mock_delete_recreate = mocker.patch(
        'apps.fyle.tasks.delete_expense_group_and_related_data',
        return_value=None
    )

    result = process_expense_group_for_fund_source_update(
        expense_group=expense_group, 
        changed_expense_ids=changed_expense_ids, 
        workspace_id=workspace_id,
        report_id='rp1s1L3QtMpF',
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids}
    )

    assert mock_delete_recreate.call_count == 1
    assert result is True


def test_delete_and_recreate_expense_group(db, mocker, add_fyle_credentials):
    """
    Test delete and recreate expense group
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    workspace_id = 1

    TaskLog.objects.filter(expense_group_id=expense_group.id).delete()

    task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='CREATING_JOURNAL_ENTRY',
        expense_group_id=expense_group.id,
        status='FAILED'
    )

    error = Error.objects.create(
        workspace_id=workspace_id,
        expense_group_id=expense_group.id,
        type='NETSUITE_ERROR'
    )

    # Create error with mapping_error_expense_group_ids
    error_with_mapping = Error.objects.create(
        workspace_id=workspace_id,
        type='MAPPING',
        mapping_error_expense_group_ids=[expense_group.id, 999]
    )

    mocker.patch(
        'apps.fyle.tasks.recreate_expense_groups',
        return_value=None
    )

    delete_expense_group_and_related_data(expense_group=expense_group, workspace_id=workspace_id)

    assert not ExpenseGroup.objects.filter(id=expense_group.id).exists()
    assert not TaskLog.objects.filter(id=task_log.id).exists()
    assert not Error.objects.filter(id=error.id).exists()
    error_with_mapping.refresh_from_db()
    assert expense_group.id not in error_with_mapping.mapping_error_expense_group_ids
    assert 999 in error_with_mapping.mapping_error_expense_group_ids
    error_with_mapping.delete()


def test_delete_and_recreate_expense_group_empty_mapping_error(db, mocker, add_fyle_credentials):
    """
    Test delete and recreate expense group with empty mapping error
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    workspace_id = 1

    error_with_mapping = Error.objects.create(
        workspace_id=workspace_id,
        type='MAPPING',
        mapping_error_expense_group_ids=[expense_group.id]
    )

    mocker.patch(
        'apps.fyle.tasks.recreate_expense_groups',
        return_value=None
    )

    delete_expense_group_and_related_data(expense_group=expense_group, workspace_id=workspace_id)

    assert not Error.objects.filter(id=error_with_mapping.id).exists()


def test_recreate_expense_groups(db, mocker, add_fyle_credentials):
    """
    Test recreate expense groups
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    workspace_id = 1
    expenses = Expense.objects.filter(workspace_id=workspace_id)
    expense_ids = [expenses.first().id]

    mock_create_groups = mocker.patch(
        'apps.fyle.models.ExpenseGroup.create_expense_groups_by_report_id_fund_source',
        return_value=[expense_ids[0]]
    )

    # Mock mark_expenses_as_skipped to return some expenses
    mock_expense = mocker.MagicMock()
    mock_expense.id = expense_ids[0]
    mocker.patch(
        'apps.fyle.tasks.mark_expenses_as_skipped',
        return_value=[mock_expense]
    )

    mock_post_summary = mocker.patch(
        'apps.fyle.tasks.post_accounting_export_summary',
        return_value=None
    )

    recreate_expense_groups(workspace_id=workspace_id, expense_ids=expense_ids)

    assert mock_create_groups.call_count == 1
    assert mock_post_summary.call_count == 1


def test_recreate_expense_groups_with_configuration_filters(db, mocker, add_fyle_credentials):
    """
    Test recreate expense groups with configuration and filters
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    workspace_id = 1
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    expenses = Expense.objects.filter(workspace_id=workspace_id)
    expense_ids = [expense.id for expense in expenses]

    mock_create_groups = mocker.patch(
        'apps.fyle.models.ExpenseGroup.create_expense_groups_by_report_id_fund_source',
        return_value=[]
    )

    mocker.patch(
        'apps.fyle.tasks.skip_expenses_and_post_accounting_export_summary',
        return_value=None
    )

    configuration.reimbursable_expenses_object = None
    configuration.save()

    recreate_expense_groups(workspace_id=workspace_id, expense_ids=expense_ids)

    configuration.reimbursable_expenses_object = 'BILL'
    configuration.corporate_credit_card_expenses_object = None
    configuration.save()

    recreate_expense_groups(workspace_id=workspace_id, expense_ids=expense_ids)

    assert mock_create_groups.call_count >= 1


def test_schedule_task_for_expense_group_fund_source_change(db, mocker, add_fyle_credentials):
    """
    Test schedule task for expense group fund source change
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    workspace_id = 1
    expense = Expense.objects.filter(workspace_id=workspace_id).first()
    changed_expense_ids = [expense.id]

    schedule_task_for_expense_group_fund_source_change(
        changed_expense_ids=changed_expense_ids,
        workspace_id=workspace_id,
        report_id='rp1s1L3QtMpF',
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids}
    )

    assert Schedule.objects.filter(
        func='apps.fyle.tasks.handle_fund_source_changes_for_expense_ids',
        name__startswith='fund_source_change_retry_'
    ).exists() is True


def test_schedule_task_existing_schedule(db, mocker, add_fyle_credentials):
    """
    Test schedule task when schedule already exists
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    workspace_id = 1
    expense = Expense.objects.filter(workspace_id=workspace_id).first()
    changed_expense_ids = [expense.id]

    # Generate the same task name that the function will generate
    hashed_name = hashlib.md5(str(changed_expense_ids).encode('utf-8')).hexdigest()[0:6]
    task_name = f'fund_source_change_retry_{hashed_name}_{workspace_id}'
    
    existing_schedule = Schedule.objects.create(
        func='apps.fyle.tasks.handle_fund_source_changes_for_expense_ids',
        name=task_name,
        args='[]'
    )

    mock_schedule = mocker.patch(
        'apps.fyle.tasks.schedule',
        return_value=None
    )

    report_id = expense.report_id
    
    schedule_task_for_expense_group_fund_source_change(
        changed_expense_ids=changed_expense_ids,
        workspace_id=workspace_id,
        report_id=report_id,
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids}
    )

    assert mock_schedule.call_count == 0
    existing_schedule.delete()


def test_cleanup_scheduled_task_exists(db, mocker, add_fyle_credentials):
    """
    Test cleanup scheduled task when task exists
    """
    workspace_id = 1
    task_name = 'test_task_name'

    schedule_obj = Schedule.objects.create(
        func='apps.fyle.tasks.handle_fund_source_changes_for_expense_ids',
        name=task_name,
        args='[]'
    )

    cleanup_scheduled_task(task_name=task_name, workspace_id=workspace_id)

    assert not Schedule.objects.filter(id=schedule_obj.id).exists()


def test_cleanup_scheduled_task_not_exists(db, mocker, add_fyle_credentials):
    """
    Test cleanup scheduled task when task doesn't exist
    """
    workspace_id = 1
    task_name = 'non_existent_task'

    # This should not raise any exception
    cleanup_scheduled_task(task_name=task_name, workspace_id=workspace_id)

    # Verify no schedules exist with this name
    assert not Schedule.objects.filter(name=task_name).exists()


def test_handle_fund_source_changes_no_affected_groups(db, mocker, add_fyle_credentials):
    """
    Test handle fund source changes when no affected groups are found
    """
    workspace_id = 1
    changed_expense_ids = [999999]  # Non-existent expense ID
    report_id = 'non_existent_report'

    mock_construct_filter = mocker.patch(
        'apps.fyle.tasks.construct_filter_for_affected_expense_groups',
        return_value=Q(id__in=[])
    )

    handle_fund_source_changes_for_expense_ids(
        workspace_id=workspace_id,
        changed_expense_ids=changed_expense_ids,
        report_id=report_id,
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids},
        task_name='test_task'
    )

    assert mock_construct_filter.call_count == 1


def test_handle_fund_source_changes_not_all_groups_exported(db, mocker, add_fyle_credentials):
    """
    Test handle fund source changes when not all expense groups are exported
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    workspace_id = 1
    expense = Expense.objects.filter(workspace_id=workspace_id).first()
    changed_expense_ids = [expense.id]
    report_id = expense.report_id

    # Mock process_expense_group_for_fund_source_update to return False
    mock_process_expense_group = mocker.patch(
        'apps.fyle.tasks.process_expense_group_for_fund_source_update',
        return_value=False
    )

    mock_recreate = mocker.patch(
        'apps.fyle.tasks.recreate_expense_groups',
        return_value=None
    )

    mock_cleanup = mocker.patch(
        'apps.fyle.tasks.cleanup_scheduled_task',
        return_value=None
    )

    handle_fund_source_changes_for_expense_ids(
        workspace_id=workspace_id,
        changed_expense_ids=changed_expense_ids,
        report_id=report_id,
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids},
        task_name='test_task'
    )

    # The function creates 2 expense groups (PERSONAL and CCC) so it should be called twice
    assert mock_process_expense_group.call_count == 2
    assert mock_recreate.call_count == 0
    assert mock_cleanup.call_count == 0


def test_recreate_expense_groups_no_expenses_found(db, mocker, add_fyle_credentials):
    """
    Test recreate expense groups when no expenses are found
    """
    workspace_id = 1
    expense_ids = [999999]  # Non-existent expense IDs

    mock_create_groups = mocker.patch(
        'apps.fyle.models.ExpenseGroup.create_expense_groups_by_report_id_fund_source',
        return_value=[]
    )

    recreate_expense_groups(workspace_id=workspace_id, expense_ids=expense_ids)

    assert mock_create_groups.call_count == 0


def test_recreate_expense_groups_with_expense_filters(db, mocker, add_fyle_credentials):
    """
    Test recreate expense groups with expense filters
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    workspace_id = 1
    expense = Expense.objects.filter(workspace_id=workspace_id).first()
    expense_ids = [expense.id]

    # Create an expense filter
    expense_filter = ExpenseFilter.objects.create(
        workspace_id=workspace_id,
        condition='category',
        operator='in',
        values=['Travel'],
        rank=1
    )

    mock_construct_filter_query = mocker.patch(
        'apps.fyle.tasks.construct_expense_filter_query',
        return_value=Q()
    )

    mock_skip_expenses = mocker.patch(
        'apps.fyle.tasks.skip_expenses_and_post_accounting_export_summary',
        return_value=None
    )

    mock_create_groups = mocker.patch(
        'apps.fyle.models.ExpenseGroup.create_expense_groups_by_report_id_fund_source',
        return_value=[]
    )

    recreate_expense_groups(workspace_id=workspace_id, expense_ids=expense_ids)

    assert mock_construct_filter_query.call_count == 1
    assert mock_skip_expenses.call_count == 1
    assert mock_create_groups.call_count == 1

    expense_filter.delete()


def test_process_expense_group_failed_status(db, mocker, add_fyle_credentials):
    """
    Test process expense group when task log is FAILED
    """
    # Create test expenses using existing pattern
    workspace = Workspace.objects.get(id=1)
    test_expenses = data['group_and_save_expense_groups_expenses']
    task_log_temp, _ = TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={'status': 'IN_PROGRESS'}
    )
    
    # Create expense groups using existing function
    group_expenses_and_save(test_expenses, task_log_temp, workspace)
    
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    workspace_id = 1
    changed_expense_ids = [expense_group.expenses.first().id]

    TaskLog.objects.filter(expense_group_id=expense_group.id).delete()

    task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='CREATING_JOURNAL_ENTRY',
        expense_group_id=expense_group.id,
        status='FAILED'
    )

    mock_delete_recreate = mocker.patch(
        'apps.fyle.tasks.delete_expense_group_and_related_data',
        return_value=None
    )

    result = process_expense_group_for_fund_source_update(
        expense_group=expense_group, 
        changed_expense_ids=changed_expense_ids, 
        workspace_id=workspace_id,
        report_id='rp1s1L3QtMpF',
        affected_fund_source_expense_ids={'PERSONAL': changed_expense_ids}
    )
    task_log.delete()

    assert mock_delete_recreate.call_count == 1
    assert result is True


def test_delete_expense_group_with_reimbursement_task_log(setup_expense_groups_for_deletion_test, mocker):
    """
    Test delete expense group excludes reimbursement and AP payment task logs
    """
    test_data = setup_expense_groups_for_deletion_test
    expense_group = test_data['expense_group_1']
    reimbursement_task_log = test_data['reimbursement_task_log'] 
    ap_payment_task_log = test_data['ap_payment_task_log']
    regular_task_log = test_data['regular_task_log']
    workspace_id = test_data['workspace_id']

    mocker.patch(
        'apps.fyle.tasks.recreate_expense_groups',
        return_value=None
    )

    delete_expense_group_and_related_data(expense_group=expense_group, workspace_id=workspace_id)

    # Reimbursement and AP payment task logs should still exist
    assert TaskLog.objects.filter(id=reimbursement_task_log.id).exists()
    assert TaskLog.objects.filter(id=ap_payment_task_log.id).exists()

    # Regular task log should be deleted
    assert not TaskLog.objects.filter(id=regular_task_log.id).exists()

    # Expense group should be deleted
    assert not ExpenseGroup.objects.filter(id=expense_group.id).exists()

