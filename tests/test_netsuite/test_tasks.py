import pytest
import json

from django.urls import reverse
from apps.fyle.models import ExpenseGroup
from apps.workspaces.models import Configuration
from tests.helper import dict_compare_keys
from apps.tasks.models import TaskLog
from apps.netsuite.tasks import __validate_general_mapping, __validate_subsidiary_mapping, get_or_create_credit_card_vendor, create_bill, create_expense_report
from apps.mappings.models import GeneralMapping
from fyle_accounting_mappings.models import DestinationAttribute
from tests.test_fyle.conftest import create_expense_group
from tests.test_mappings.conftest import create_configuration, create_general_mapping
from .fixtures import data

@pytest.mark.django_db()
def test_general_mapping_do_not_exists(create_expense_group, create_configuration):

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    configuration = Configuration.objects.filter(workspace_id=1).first()
    general_mappings_errors = __validate_general_mapping(expense_group, configuration)

    assert general_mappings_errors[0]['message'] == 'General Mappings not found'

@pytest.mark.django_db()
def test_accounts_payable_missing(create_expense_group, create_general_mapping):

    configuration = Configuration.objects.get(workspace_id=1)
    general_mappings = GeneralMapping.objects.get(workspace_id=1)
    
    general_mappings.accounts_payable_name = None
    general_mappings.accounts_payable_id = None
    general_mappings.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    general_mappings_errors = __validate_general_mapping(expense_group, configuration)
    
    assert general_mappings_errors[0]['message'] == 'Accounts Payable not found'

    configuration.reimbursable_expenses_object = 'JOURNAL ENTRY'
    configuration.corporate_credit_card_expenses_object = 'JOURNAL ENTRY'
    configuration.employee_field_mapping = 'VENDOR'
    
    configuration.save()
    general_mappings_errors = __validate_general_mapping(expense_group, configuration)
    assert general_mappings_errors[0]['message'] == 'Accounts Payable not found'

def test_reimbursable_account_missing(create_expense_group, create_general_mapping):
    configuration = Configuration.objects.get(workspace_id=1)
    general_mappings = GeneralMapping.objects.get(workspace_id=1)

    general_mappings.reimbursable_account_id = None
    general_mappings.reimbursable_account_name = None

    configuration.reimbursable_expenses_object = 'EXPENSE REPORT'
    configuration.save()
    general_mappings.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    general_mappings_errors = __validate_general_mapping(expense_group, configuration)
    assert general_mappings_errors[0]['message'] == 'Reimbursable Account not found'

def test_default_credit_card_account_not_found(create_expense_group, create_general_mapping):
    configuration = Configuration.objects.get(workspace_id=1)
    general_mappings = GeneralMapping.objects.get(workspace_id=1)

    general_mappings.default_ccc_account_id = None
    general_mappings.default_ccc_account_name = None
    general_mappings.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expense_group.fund_source = 'CCC'
    expense_group.save()
    general_mappings_errors = __validate_general_mapping(expense_group, configuration)
    assert general_mappings_errors[0]['message'] == 'Default Credit Card Account not found'

    configuration.corporate_credit_card_expenses_object = 'JOURNAL ENTRY'
    configuration.save()

    general_mappings_errors = __validate_general_mapping(expense_group, configuration)
    assert general_mappings_errors[0]['message'] == 'Default Credit Card Account not found'

def test_subsidary_mapping_not_found(create_expense_group):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    errors = __validate_subsidiary_mapping(expense_group)

    assert errors == []

def test_get_or_create_credit_card_vendor(create_expense_group, create_general_mapping):
    configuration = Configuration.objects.get(workspace_id=1)
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    merchant = 'Uber BV'
    auto_create_merchants = configuration.auto_create_merchants

    vendor = get_or_create_credit_card_vendor(expense_group, merchant, auto_create_merchants)
    
    created_vendor = DestinationAttribute.objects.filter(
        workspace_id=1,
        value='Uber BV'
    ).first()
    
    assert created_vendor.destination_id == '12106'
    assert created_vendor.display_name == 'vendor'

def test_post_bill_success(create_expense_group, create_general_mapping, create_necessary_mapping, mocker):

    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.post_bill',
        return_value=data['bill_response']
    )

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    create_bill(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    
    assert task_log.detail == data['bill_response']
    assert task_log.status == 'COMPLETE'

def test_post_bill_mapping_error(create_expense_group, create_general_mapping, mocker):
    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.post_bill',
        return_value=data['bill_response']
    )

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    create_bill(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(workspace_id=1).first()

    assert task_log.detail[0]['message'] == 'Employee mapping not found'
    assert task_log.detail[1]['message'] == 'Category Mapping Not Found'
    assert task_log.status == 'FAILED'

@pytest.skip
def test_create_expense_report(create_expense_group, create_general_mapping, create_necessary_mapping, mocker):
    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.post_expense_report',
        return_value=data['bill_response']
    )

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    create_expense_report(expense_group, task_log.id)

    assert task_log.detail == data['expense_response']
    assert task_log.status == 'COMPLETE'