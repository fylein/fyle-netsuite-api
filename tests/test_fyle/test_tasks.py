from cmath import exp
import pytest
from fyle_integrations_platform_connector import PlatformConnector
import json
from apps.fyle.models import ExpenseFilter, ExpenseGroup, Expense, ExpenseGroupSettings
from apps.tasks.models import TaskLog
from apps.fyle.tasks import create_expense_groups, schedule_expense_group_creation
from apps.workspaces.models import Configuration, FyleCredential, Workspace
from .fixtures import data
from django.urls import reverse
from tests.helper import dict_compare_keys
from unittest import mock


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

        create_expense_groups(1, configuration, ['PERSONAL', 'CCC'], task_log)

        expense_group = ExpenseGroup.objects.filter(workspace_id=1)
        expenses = Expense.objects.filter(org_id='or79Cob97KSh')
        
        assert len(expense_group) == expense_group_count+2
        assert len(expenses) == expenses_count+2

        fyle_credential = FyleCredential.objects.get(workspace_id=1)
        fyle_credential.delete()

        create_expense_groups(1, configuration, ['PERSONAL', 'CCC'], task_log)

        task_log = TaskLog.objects.get(workspace_id=1)
        assert task_log.detail['message'] == 'Fyle credentials do not exist in workspace'
        assert task_log.status == 'FAILED'

        expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=1)
        expense_group_settings.delete()

        create_expense_groups(1, configuration, ['PERSONAL', 'CCC'], task_log)

        task_log = TaskLog.objects.get(workspace_id=1)
        assert task_log.status == 'FATAL' 


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

        create_expense_groups(1, configuration, ['PERSONAL', 'CCC'], task_log)
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
