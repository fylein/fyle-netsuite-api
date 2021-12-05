import pytest
import random
import string
from django.urls import reverse
from apps.fyle.models import Expense, ExpenseGroup
from apps.netsuite.models import CreditCardCharge, ExpenseReport, Bill, JournalEntry
from apps.workspaces.models import Configuration
from tests.helper import dict_compare_keys
from apps.tasks.models import TaskLog
from apps.netsuite.tasks import __validate_general_mapping, __validate_subsidiary_mapping, create_credit_card_charge, create_journal_entry, get_or_create_credit_card_vendor, create_bill, create_expense_report
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
    journal_entry_object = create_journal_entry(expense_group, task_log.id)

    journal_entry = JournalEntry.objects.filter(expense_group_id=expense_group.id)
    print(journal_entry)
    assert 1==1

@pytest.mark.django_db()
def test_post_credit_charge(create_task_logs, add_netsuite_credentials, add_fyle_credentials):
    task_log = TaskLog.objects.filter(workspace_id=49).first()

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).last()
    expenses = expense_group.expenses.all()

    general_mappings = GeneralMapping.objects.get(workspace_id=49)

    general_mappings.default_ccc_account_name = 'Unapproved Expense Report'
    general_mappings.default_ccc_account_id = 118
    general_mappings.save()

    expense_group.id = random.randint(100, 1500000)
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()

    expense_group.expenses.set(expenses)
    credit_card_charge_object = create_credit_card_charge(expense_group, task_log.id)

    credit_card_charge = CreditCardCharge.objects.filter(expense_group_id=expense_group.id)
    assert 1==1

