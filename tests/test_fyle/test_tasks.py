import pytest
import json
from django.db.models import Q
from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum

from apps.fyle.models import ExpenseGroup, Expense, ExpenseGroupSettings
from apps.tasks.models import TaskLog
from apps.fyle.actions import post_accounting_export_summary
from apps.fyle.tasks import (
    create_expense_groups,
    import_and_export_expenses,
    schedule_expense_group_creation,
    skip_expenses_and_post_accounting_export_summary,
    update_non_exported_expenses
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
