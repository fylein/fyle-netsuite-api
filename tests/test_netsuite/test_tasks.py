import pytest
import random
import string
from datetime import datetime
from django.urls import reverse
from apps.fyle.models import Expense, ExpenseGroup
from apps.netsuite.connector import NetSuiteConnector
from apps.netsuite.models import CreditCardCharge, ExpenseReport, Bill, JournalEntry
from apps.workspaces.models import Configuration, NetSuiteCredentials
from tests.helper import dict_compare_keys
from apps.tasks.models import TaskLog
from apps.netsuite.tasks import __validate_general_mapping, __validate_subsidiary_mapping, check_expenses_reimbursement_status, check_netsuite_object_status, create_credit_card_charge, create_journal_entry, create_netsuite_payment_objects, create_or_update_employee_mapping, create_vendor_payment, get_all_internal_ids, \
     get_or_create_credit_card_vendor, create_bill, create_expense_report, load_attachments, __handle_netsuite_connection_error
from apps.mappings.models import GeneralMapping
from fyle_accounting_mappings.models import DestinationAttribute, EmployeeMapping, CategoryMapping
from .fixtures import data


def random_char(char_num):
       return ''.join(random.choice(string.ascii_letters) for _ in range(char_num))

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
def test_post_bill_success(create_task_logs, add_netsuite_credentials, add_fyle_credentials):


    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.get(id=2)
    expenses = expense_group.expenses.all()

    expense_group.id = random.randint(100, 1500000)
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)
    
    create_bill(expense_group, task_log.id)
    
    task_log = TaskLog.objects.get(pk=task_log.id)
    bill = Bill.objects.get(expense_group_id=expense_group.id)
    assert task_log.status=='COMPLETE'
    assert bill.entity_id=='1674'
    assert bill.currency=='1'
    assert bill.location_id=='8'
    assert bill.accounts_payable_id=='25'
    

@pytest.mark.django_db()
def test_post_bill_mapping_error(create_task_logs, add_netsuite_credentials, add_fyle_credentials):

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    CategoryMapping.objects.filter(workspace_id=1).delete()
    EmployeeMapping.objects.filter(workspace_id=1).delete()

    expense_group = ExpenseGroup.objects.get(id=2)
    create_bill(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(pk=task_log.id).first()

    assert task_log.detail[0]['message'] == 'Employee mapping not found'
    assert task_log.detail[1]['message'] == 'Category Mapping Not Found'
    assert task_log.status == 'FAILED'

@pytest.mark.django_db()
def test_accounting_period_working(create_task_logs, add_netsuite_credentials, add_fyle_credentials):
    task_log = TaskLog.objects.filter(workspace_id=1).first()

    expense_group = ExpenseGroup.objects.get(id=2)
    expenses = expense_group.expenses.all()

    expense_group.id = random.randint(100, 1500000)
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)

    spent_at = {'spent_at': '2012-09-14T00:00:00'}
    expense_group.description.update(spent_at)
    create_bill(expense_group, task_log.id)
    
    task_log = TaskLog.objects.get(pk=task_log.id)

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    assert task_log.detail[0]['message'] == 'An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.change_accounting_period = True
    configuration.save()

    create_bill(expense_group, task_log.id)
    bill = Bill.objects.get(expense_group_id=expense_group.id)
    task_log = TaskLog.objects.get(pk=task_log.id)

    assert task_log.status=='COMPLETE'
    assert bill.entity_id=='1674'
    assert bill.currency=='1'
    assert bill.location_id=='8'
    assert bill.accounts_payable_id=='25'

@pytest.mark.django_db()
def test_create_expense_report(create_task_logs, add_netsuite_credentials, add_fyle_credentials):

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    expense_group.id = random.randint(100, 1500000)
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)
    create_expense_report(expense_group, task_log.id)
    expense_report = ExpenseReport.objects.get(expense_group_id=expense_group.id)

    assert expense_report.account_id=='118'
    assert expense_report.entity_id=='1676'
    assert expense_report.expense_group_id==expense_group.id
    assert expense_report.subsidiary_id == '3'


    task_log = TaskLog.objects.filter(workspace_id=1).last()
    task_log.status = 'READY'
    task_log.save()
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_credentials.delete()

    create_expense_report(expense_group, task_log.id)

    final_task_log = TaskLog.objects.get(id=task_log.id)
    final_task_log.detail['message'] == 'NetSuite Account not connected'

@pytest.mark.django_db()
def test_post_journal_entry(create_task_logs, add_netsuite_credentials, add_fyle_credentials):
    task_log = TaskLog.objects.filter(workspace_id=49).first()

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).first()
    expenses = expense_group.expenses.all()

    expense_group.id = random.randint(100, 1500000)
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()

    expense_group.expenses.set(expenses)
    create_journal_entry(expense_group, task_log.id)

    journal_entry = JournalEntry.objects.filter(expense_group_id=expense_group.id).first()

    assert journal_entry.currency == '1'
    assert journal_entry.location_id == '10'
    assert journal_entry.memo == 'Reimbursable expenses by admin1@fyleforintacct.in'


@pytest.mark.django_db()
def test_post_credit_charge(create_task_logs, add_netsuite_credentials, add_fyle_credentials):
    task_log = TaskLog.objects.filter(workspace_id=49).first()

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).last()
    expenses = expense_group.expenses.all()

    general_mappings = GeneralMapping.objects.get(workspace_id=49)

    general_mappings.default_ccc_account_name = 'Aus Account'
    general_mappings.default_ccc_account_id = 228
    general_mappings.save()

    expense_group.id = random.randint(100, 1500000)
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()

    expense_group.expenses.set(expenses)
    create_credit_card_charge(expense_group, task_log.id)

    credit_card_charge = CreditCardCharge.objects.filter(expense_group_id=expense_group.id).first()
    assert credit_card_charge.credit_card_account_id == '228'
    assert credit_card_charge.memo == 'Credit card expenses by admin1@fyleforintacct.in'

@pytest.mark.django_db()
def test_get_all_internal_ids(create_expense_report, create_task_logs):
    expense_reports = ExpenseReport.objects.all()
    internal_ids = get_all_internal_ids(expense_reports)
    
    assert internal_ids[1]['internal_id'] == 10913

@pytest.mark.django_db()
def test_check_netsuite_object_status(create_expense_report, create_task_logs):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    expense_report = ExpenseReport.objects.filter(expense_group__id=expense_group.id).first()
    assert expense_report.paid_on_netsuite == False

    check_netsuite_object_status(1)

    expense_report = ExpenseReport.objects.filter(expense_group__id=expense_group.id).first()
    assert expense_report.paid_on_netsuite == True


def test_load_attachments(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)


    attachment = load_attachments(netsuite_connection, 'tx3asPlm9wyF', expense_group)
    
    assert attachment != None


def test_create_or_update_employee_mapping(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id=1)

    create_or_update_employee_mapping(expense_group, netsuite_connection, 'EMAIL', 'EMPLOYEE')


    expense_group.description['employee_email'] = 'jhonsnow@gmail.com'
    expense_group.save()

    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()

    create_or_update_employee_mapping(expense_group, netsuite_connection, 'EMAIL', 'EMPLOYEE')

    new_employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()

    assert new_employee_mappings == employee_mappings + 1

    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).last()

    assert employee_mappings.destination_employee_id == 5436


def test_handle_netsuite_connection_error(db):

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=1
    )

    __handle_netsuite_connection_error(expense_group, task_log)

    task_log = TaskLog.objects.filter(workspace_id=1).last()

    assert task_log.status == 'FAILED'
    assert task_log.detail['message'] == 'NetSuite Account not connected'
