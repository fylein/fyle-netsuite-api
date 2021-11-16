import pytest
import json

from django.urls import reverse
from apps.fyle.models import ExpenseGroup
from apps.netsuite.models import ExpenseReport, Bill
from apps.workspaces.models import Configuration
from tests.helper import dict_compare_keys
from apps.tasks.models import TaskLog
from apps.netsuite.tasks import __validate_general_mapping, __validate_subsidiary_mapping, get_or_create_credit_card_vendor, create_bill, create_expense_report
from apps.mappings.models import GeneralMapping
from fyle_accounting_mappings.models import DestinationAttribute
from .fixtures import data

@pytest.mark.django_db()
def test_accounts_payable_missing():

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

@pytest.mark.django_db()
def test_reimbursable_account_missing():
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

@pytest.mark.django_db()
def test_default_credit_card_account_not_found():
    configuration = Configuration.objects.get(workspace_id=1)
    general_mappings = GeneralMapping.objects.get(workspace_id=1)

    general_mappings.default_ccc_account_id = None
    general_mappings.default_ccc_account_name = None
    general_mappings.save()

    expense_group = ExpenseGroup.objects.get(id=2)
    configuration.corporate_credit_card_expenses_object = 'JOURNAL ENTRY'
    configuration.save()

    general_mappings_errors = __validate_general_mapping(expense_group, configuration)
    assert general_mappings_errors[0]['message'] == 'Default Credit Card Account not found'

@pytest.mark.django_db()
def test_subsidary_mapping_not_found():
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    errors = __validate_subsidiary_mapping(expense_group)

    assert errors == []

@pytest.mark.django_db()
def test_get_or_create_credit_card_vendor(add_netsuite_credentials):
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

@pytest.mark.django_db()
def test_post_bill_success(create_task_logs, add_netsuite_credentials):


    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.get(id=2)
    create_bill(expense_group, task_log.id)
    
    task_log = TaskLog.objects.filter(workspace_id=1).first()
    bill = Bill.objects.get(expense_group_id='2')
    assert task_log.status=='COMPLETE'
    assert bill.entity_id=='1674'
    assert bill.currency=='1'
    assert bill.location_id=='8'
    assert bill.accounts_payable_id=='25'
    

@pytest.mark.skip
def test_post_bill_mapping_error(mocker):
    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.post_bill',
        return_value=data['bill_response']
    )

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1, id=2)
    create_bill(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(workspace_id=1).first()

    assert task_log.detail[0]['message'] == 'Employee mapping not found'
    assert task_log.detail[1]['message'] == 'Category Mapping Not Found'
    assert task_log.status == 'FAILED'

@pytest.mark.django_db()
def test_create_expense_report(create_task_logs, add_netsuite_credentials):

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    create_expense_report(expense_group, task_log.id)
    expense_report = ExpenseReport.objects.get(expense_group_id='1')

    assert expense_report.account_id=='118'
    assert expense_report.entity_id=='1676'
    assert expense_report.expense_group_id==1
    assert expense_report.subsidiary_id == '3'
