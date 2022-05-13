import pytest
import random
import string
import logging
from django_q.models import Schedule
from pytest_mock import mocker
from apps.fyle.models import ExpenseGroup, Reimbursement, Expense
from apps.netsuite.connector import NetSuiteConnector
from apps.netsuite.models import CreditCardCharge, ExpenseReport, Bill, JournalEntry, VendorPayment, VendorPaymentLineitem
from apps.workspaces.models import Configuration, NetSuiteCredentials
from apps.tasks.models import TaskLog
from apps.netsuite.tasks import __validate_general_mapping, __validate_subsidiary_mapping, check_netsuite_object_status, create_credit_card_charge, create_journal_entry, create_or_update_employee_mapping, create_vendor_payment, get_all_internal_ids, \
     get_or_create_credit_card_vendor, create_bill, create_expense_report, load_attachments, __handle_netsuite_connection_error, process_reimbursements, process_vendor_payment, schedule_bills_creation, schedule_credit_card_charge_creation, schedule_expense_reports_creation, schedule_journal_entry_creation, schedule_netsuite_objects_status_sync, schedule_reimbursements_sync, schedule_vendor_payment_creation, \
        __validate_tax_group_mapping, check_expenses_reimbursement_status
from apps.mappings.models import GeneralMapping
from fyle_accounting_mappings.models import DestinationAttribute, EmployeeMapping, CategoryMapping, ExpenseAttribute
from .fixtures import data
from apps.workspaces.models import NetSuiteCredentials, Configuration


logger = logging.getLogger(__name__)
logger.level = logging.INFO

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

    get_or_create_credit_card_vendor(expense_group, merchant, True)


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

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.auto_map_employees = 'NAME'
    configuration.auto_create_destination_entity = True
    configuration.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    source_employee = ExpenseAttribute.objects.get(
        workspace_id=expense_group.workspace_id,
        attribute_type='EMPLOYEE',
        value=expense_group.description.get('employee_email')
    )
    source_employee.value = 'new_employeeee@fyle.in'
    source_employee.detail.update({'full_name': 'Fyle new employeeee'})
    source_employee.save()

    expense_group.description.update({'employee_email': 'new_employeeee@fyle.in'})
    expense_group.save()

    expenses = expense_group.expenses.all()

    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    general_mapping.location_name = "01: San Francisco"
    general_mapping.location_id = 2
    general_mapping.save()
    
    for expense in expenses:
        expense.employee_email = 'new_employeeee@fyle.in'
        expense.save()
    
    expense_group.expenses.set(expenses)

    mapping = EmployeeMapping.objects.get(
        source_employee__value=expense_group.description.get('employee_email'),
        workspace_id=expense_group.workspace_id
    )
    mapping.delete()

    create_bill(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(pk=task_log.id).first()
    assert task_log.detail[0]['message'] == 'Employee mapping not found'

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_credentials.delete()
    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()
    
    create_bill(expense_group, task_log.id)

    final_task_log = TaskLog.objects.get(id=task_log.id)
    final_task_log.detail['message'] == 'NetSuite Account not connected'

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

    # assert task_log.detail[0]['message'] == 'Employee mapping not found'
    assert task_log.detail[0]['message'] == 'Category Mapping Not Found'
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
def test_create_journal_entry_mapping_error(create_task_logs, add_netsuite_credentials, add_fyle_credentials):

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    CategoryMapping.objects.filter(workspace_id=1).delete()
    EmployeeMapping.objects.filter(workspace_id=1).delete()

    expense_group = ExpenseGroup.objects.get(id=1)
    expense_group.description.update({'employee_email': 'sam@fyle.in'})
    expense_group.save()

    create_journal_entry(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(pk=task_log.id).first()

    assert task_log.detail[0]['message'] == 'Employee mapping not found'
    # assert task_log.detail[1]['message'] == 'Category Mapping Not Found'
    assert task_log.status == 'FAILED'


@pytest.mark.django_db()
def test_accounting_period_working_create_journal_entry(create_task_logs, add_netsuite_credentials, add_fyle_credentials):
    task_log = TaskLog.objects.filter(workspace_id=49).first()

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).first()
    expenses = expense_group.expenses.all()

    expense_group.id = random.randint(100, 1500000)
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)

    spent_at = {'spent_at': '1190-11-14T00:00:00'}
    expense_group.description.update(spent_at)
    create_journal_entry(expense_group, task_log.id)
    
    task_log = TaskLog.objects.get(pk=task_log.id)

    task_log = TaskLog.objects.filter(workspace_id=49).first()
    assert task_log.detail[0]['message'] == 'An error occured in a upsert request: You have entered an Invalid Field Value 11/14/1190 for the following field: trandate'


@pytest.mark.django_db()
def test_create_expense_report_mapping_error(create_task_logs, add_netsuite_credentials, add_fyle_credentials):

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    CategoryMapping.objects.filter(workspace_id=1).delete()
    EmployeeMapping.objects.filter(workspace_id=1).delete()

    expense_group = ExpenseGroup.objects.get(id=1)
    expense_group.description.update({'employee_email': 'sam@fyle.in'})
    expense_group.save()
    create_expense_report(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(pk=task_log.id).first()

    assert task_log.detail[0]['message'] == 'Employee mapping not found'
    # assert task_log.detail[1]['message'] == 'Category Mapping Not Found'
    assert task_log.status == 'FAILED'


@pytest.mark.django_db()
def test_accounting_period_working_create_expense_report(create_task_logs, add_netsuite_credentials, add_fyle_credentials):
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
    create_expense_report(expense_group, task_log.id)
    
    task_log = TaskLog.objects.get(pk=task_log.id)

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    assert task_log.detail[0]['message'] == 'An error occured in a upsert request: A credit card account has not been selected for corporate card expenses in Accounting Preferences. Your Expense Report cannot be saved, contact an administrator.'


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

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_credentials.delete()

    task_log.status = 'READY'
    task_log.save()

    create_credit_card_charge(expense_group, task_log.id)

    task_log = TaskLog.objects.get(id=task_log.id)
    assert task_log.detail['message'] == 'NetSuite Account not connected'


@pytest.mark.django_db()
def test_create_credit_card_charge_mapping_error(create_task_logs, add_netsuite_credentials, add_fyle_credentials):

    task_log = TaskLog.objects.filter(workspace_id=49).first()
    task_log.status = 'READY'
    task_log.save()

    CategoryMapping.objects.filter(workspace_id=49).delete()
    EmployeeMapping.objects.filter(workspace_id=49).delete()

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).last()

    expense_group.description.update({'employee_email': 'sam@fyle.in'})
    expense_group.save()

    create_credit_card_charge(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(pk=task_log.id).first()

    # assert task_log.detail[0]['message'] == 'Employee mapping not found'
    assert task_log.detail[0]['message'] == 'Category Mapping Not Found'
    assert task_log.status == 'FAILED'


@pytest.mark.django_db()
def test_accounting_period_working_create_credit_card_charge(create_task_logs, add_netsuite_credentials, add_fyle_credentials):
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

    spent_at = {'spent_at': '1190-09-14T00:00:00'}
    expense_group.description.update(spent_at)
    create_credit_card_charge(expense_group, task_log.id)
    
    task_log = TaskLog.objects.get(pk=task_log.id)

    task_log = TaskLog.objects.filter(workspace_id=49).first()
    # assert task_log.detail[0]['message'] == 'The transaction date you specified is not within the date range of your accounting period.'

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.change_accounting_period = True
    configuration.save()

    create_credit_card_charge(expense_group, task_log.id)
    credit_card_charge = CreditCardCharge.objects.get(expense_group_id=expense_group.id)

    task_log = TaskLog.objects.get(pk=task_log.id)

    assert task_log.status=='COMPLETE'
    assert credit_card_charge.entity_id=='12104'
    assert credit_card_charge.currency=='1'
    assert credit_card_charge.location_id=='10'


@pytest.mark.django_db()
def test_get_all_internal_ids(create_expense_report, create_task_logs):
    expense_reports = ExpenseReport.objects.all()
    internal_ids = get_all_internal_ids(expense_reports)
    
    assert internal_ids[1]['internal_id'] == 10913

@pytest.mark.django_db()
def test_check_netsuite_object_status(create_expense_report, create_task_logs, add_netsuite_credentials):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    expense_report = ExpenseReport.objects.filter(expense_group__id=expense_group.id).first()
    assert expense_report.paid_on_netsuite == False

    check_netsuite_object_status(1)

    expense_report = ExpenseReport.objects.filter(expense_group__id=expense_group.id).first()
    assert expense_report.paid_on_netsuite == True


@pytest.mark.django_db()
def test_check_netsuite_object_status_bill(add_netsuite_credentials, create_bill_task):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    
    bill, bill_lineitems = create_bill_task
    assert bill.paid_on_netsuite == False

    check_netsuite_object_status(1)

    bill = Bill.objects.filter(expense_group__id=expense_group.id).first()
    assert bill.paid_on_netsuite == True


def test_load_attachments(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)


    attachment = load_attachments(netsuite_connection, 'tx3asPlm9wyF', expense_group)
    assert attachment == None

    attachment = load_attachments(None, 'tx3asPlm9wyF', expense_group)


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

    assert employee_mappings.destination_employee_id == 5464

    expense_group.description['employee_email'] = 'ashwin.t@fyle.in'
    expense_group.save()

    general_mapping = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
    general_mapping.default_ccc_vendor_id = 1674
    general_mapping.save()

    create_or_update_employee_mapping(expense_group, netsuite_connection, 'NAME', 'VENDOR')
    new_employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert new_employee_mappings == employee_mappings

    
def test_handle_netsuite_connection_error(db):

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=1
    )

    __handle_netsuite_connection_error(expense_group, task_log)

    task_log = TaskLog.objects.filter(workspace_id=1).last()

    assert task_log.status == 'FAILED'
    assert task_log.detail['message'] == 'NetSuite Account not connected'


def test_schedule_reimbursements_sync(db):

    schedule = Schedule.objects.filter(func='apps.netsuite.tasks.process_reimbursements', args=49).count()
    assert schedule == 0

    schedule_reimbursements_sync(sync_netsuite_to_fyle_payments=True, workspace_id=49)

    schedule_count = Schedule.objects.filter(func='apps.netsuite.tasks.process_reimbursements', args=49).count()
    assert schedule_count == 1

    schedule_reimbursements_sync(sync_netsuite_to_fyle_payments=False, workspace_id=49)

    schedule_count = Schedule.objects.filter(func='apps.netsuite.tasks.process_reimbursements', args=49).count()
    assert schedule_count == 0


def test_process_reimbursements(db, mocker, add_fyle_credentials):

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Reimbursements.bulk_post_reimbursements',
        return_value=[]
    )

    reimbursement_count = Reimbursement.objects.filter(workspace_id=1).count()
    assert reimbursement_count == 1

    expenses = Expense.objects.get(id=1)
    expenses.settlement_id = 'setqi0eM6HUgZ'
    expenses.paid_on_netsuite = True
    expenses.save()

    process_reimbursements(1)

    reimbursement = Reimbursement.objects.filter(workspace_id=1).count()

    assert reimbursement == 1

def test_schedule_netsuite_objects_status_sync(db):

    schedule = Schedule.objects.filter(func='apps.netsuite.tasks.check_netsuite_object_status', args=2).count()
    assert schedule == 0

    schedule_netsuite_objects_status_sync(sync_netsuite_to_fyle_payments=True, workspace_id=2)

    schedule = Schedule.objects.filter(func='apps.netsuite.tasks.check_netsuite_object_status', args=2).count()
    assert schedule == 1

    schedule_netsuite_objects_status_sync(sync_netsuite_to_fyle_payments=False, workspace_id=2)

    schedule = Schedule.objects.filter(func='apps.netsuite.tasks.check_netsuite_object_status', args=2).first()
    assert schedule == None

def test_schedule_vendor_payment_creation(db):
    
    general_mappings = GeneralMapping.objects.get(workspace_id=1)
    general_mappings.vendor_payment_account_id = 25
    general_mappings.save()
    schedule = Schedule.objects.filter(func='apps.netsuite.tasks.create_vendor_payment', args=1).count()
    assert schedule == 0

    schedule_vendor_payment_creation(sync_fyle_to_netsuite_payments=True, workspace_id=1)

    schedule = Schedule.objects.filter(func='apps.netsuite.tasks.create_vendor_payment', args=1).count()
    assert schedule == 1

    schedule_vendor_payment_creation(sync_fyle_to_netsuite_payments=False, workspace_id=1)

    schedule = Schedule.objects.filter(func='apps.netsuite.tasks.create_vendor_payment', args=1).first()
    assert schedule == None


def test_create_vendor_payment(db, mocker, create_task_logs, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).last()
    expenses = expense_group.expenses.all()

    expense_group.id = random.randint(100, 1500000)
    expense_group.fund_source = 'PERSONAL'
    expense_group.exported_at = '2022-03-03'
    expense_group.save()

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.expense_group_id = expense_group.id
    task_log.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.fund_source = 'PERSONAL'
        expense.save()

    expense_group.expenses.set(expenses)

    create_expense_report(expense_group, task_log.id)
    
    new_task_log = TaskLog.objects.get(id=task_log.id)

    mocker.patch(
        'apps.tasks.models.TaskLog.objects.get',
        return_value=new_task_log
    )

    mocker.patch(
        'apps.netsuite.tasks.check_expenses_reimbursement_status',
        return_value=True
    )

    create_vendor_payment(1)

    task_log = TaskLog.objects.filter(workspace_id=1, status='FAILED').last()

    assert task_log.detail[0]['message'] == 'An error occured in a upsert request: Invalid apacct reference key 118.'
    assert task_log.status == 'FAILED'

    vendor_payment_lineitems = VendorPaymentLineitem.objects.all()
    vendor_payment_lineitems.delete()
    vendor_payment = VendorPayment.objects.all()
    vendor_payment.delete()


    mocker.patch(
        'netsuitesdk.api.vendor_payments.VendorPayments.post',
        return_value={'message': 'payment_object'}
    )

    create_vendor_payment(1)

    expense_report = ExpenseReport.objects.filter(expense_group_id=expense_group.id).first()

    assert expense_report.payment_synced == True
    assert expense_report.paid_on_netsuite == True


def test_create_vendor_payment_bill_object(db, mocker, create_task_logs, add_netsuite_credentials, add_fyle_credentials):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).last()
    expenses = expense_group.expenses.all()

    expense_group.id = random.randint(100, 1500000)
    expense_group.fund_source = 'PERSONAL'
    expense_group.exported_at = '2022-03-03'
    expense_group.save()

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.expense_group_id = expense_group.id
    task_log.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.fund_source = 'PERSONAL'
        expense.save()

    expense_group.expenses.set(expenses)

    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    general_mapping.location_name = "01: San Francisco"
    general_mapping.location_id = 2
    general_mapping.save()
    
    create_bill(expense_group, task_log.id)

    bill = Bill.objects.first()

    new_task_log = TaskLog.objects.get(id=task_log.id)

    mocker.patch(
        'apps.tasks.models.TaskLog.objects.get',
        return_value=new_task_log
    )

    mocker.patch(
        'apps.netsuite.tasks.check_expenses_reimbursement_status',
        return_value=True
    )

    mocker.patch(
        'netsuitesdk.api.vendor_payments.VendorPayments.post',
        return_value={'message': 'payment_object'}
    )

    create_vendor_payment(1)

    bill = Bill.objects.filter(expense_group_id=expense_group.id).first()

    assert bill.payment_synced == True
    assert bill.paid_on_netsuite == True


def test_process_vendor_payment(db, mocker):

    entity_object = data['entity_object']
    expense_group = ExpenseGroup.objects.get(id=1)
    entity_object['line'][0].update({
        'expense_group': expense_group
    })

    process_vendor_payment(entity_object, 49, 'EXPENSE_REPORT')

    task_log = TaskLog.objects.get(workspace_id=49, type='CREATING_VENDOR_PAYMENT')
    assert task_log.detail == {'message': 'NetSuite Account not connected'}


def test_process_vendor_payment_bill(db, mocker):

    entity_object = data['entity_object']
    expense_group = ExpenseGroup.objects.get(id=1)
    entity_object['line'][0].update({
        'expense_group': expense_group
    })

    process_vendor_payment(entity_object, 49, 'BILL')

    task_log = TaskLog.objects.get(workspace_id=49, type='CREATING_VENDOR_PAYMENT')
    assert task_log.detail == {'message': 'NetSuite Account not connected'}


def test_schedule_netsuite_entity_creation(db):

    expense_group = ExpenseGroup.objects.get(id=1)

    schedule_expense_reports_creation(1, ['1'])

    task_logs = TaskLog.objects.get(workspace_id=1, expense_group=expense_group)

    assert task_logs.status == 'ENQUEUED'
    assert task_logs.type == 'CREATING_EXPENSE_REPORT'

    expense_group = ExpenseGroup.objects.get(id=3)

    schedule_journal_entry_creation(2, ['3'])

    task_logs = TaskLog.objects.get(workspace_id=2, expense_group=expense_group)

    assert task_logs.status == 'ENQUEUED'
    assert task_logs.type == 'CREATING_JOURNAL_ENTRY'


    expense_group = ExpenseGroup.objects.get(id=2)

    schedule_bills_creation(1, ['2'])

    task_logs = TaskLog.objects.get(workspace_id=1, expense_group=expense_group)

    assert task_logs.status == 'ENQUEUED'
    assert task_logs.type == 'CREATING_BILL'

    expense_group = ExpenseGroup.objects.get(id=48)

    schedule_credit_card_charge_creation(49, ['48'])

    task_logs = TaskLog.objects.get(workspace_id=49, expense_group=expense_group)

    assert task_logs.status == 'ENQUEUED'
    assert task_logs.type == 'CREATING_CREDIT_CARD_CHARGE'


@pytest.mark.django_db()
def test__validate_tax_group_mapping(db):
    expense_group = ExpenseGroup.objects.get(id=3)
    configuration = Configuration.objects.get(id=2)
    errs = __validate_tax_group_mapping(expense_group, configuration)
    assert errs == []


@pytest.mark.django_db()
def test_check_expenses_reimbursement_status(db):
    expenses = Expense.objects.filter(id=1)
    expenses[0].settlement_id = 'setqi0eM6HUgZ'
    expenses[0].save()

    status = check_expenses_reimbursement_status(expenses)
    assert status == False


# insert into mapping_settings (source_field, destination_field, created_at, updated_at, workspace_id, import_to_fyle, is_custom) values ('CORPORATE_CARD', 'CREDIT_CARD_ACCOUNT', now(), now(), 49, 't', 'f');
# insert into workspace_schedules (enabled, start_datetime, interval_hours, workspace_id, emails_selected) values ('t', now(), 1, 49, '{owner@fyleforintacct.in}');
