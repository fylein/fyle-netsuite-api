import json
from unittest import mock
import pytest
import random
import string
import logging
from django_q.models import Schedule
from netsuitesdk import NetSuiteRequestError
from apps.fyle.models import ExpenseGroup, Reimbursement, Expense
from apps.netsuite.connector import NetSuiteConnector
from apps.netsuite.models import CreditCardCharge, ExpenseReport, Bill, JournalEntry
from apps.workspaces.models import Configuration, NetSuiteCredentials
from apps.tasks.models import TaskLog
from apps.netsuite.tasks import __validate_general_mapping, __validate_subsidiary_mapping, check_netsuite_object_status, create_credit_card_charge, create_journal_entry, create_or_update_employee_mapping, create_vendor_payment, get_all_internal_ids, \
     get_or_create_credit_card_vendor, create_bill, create_expense_report, load_attachments, __handle_netsuite_connection_error, process_reimbursements, process_vendor_payment, schedule_bills_creation, schedule_credit_card_charge_creation, schedule_expense_reports_creation, schedule_journal_entry_creation, schedule_netsuite_objects_status_sync, schedule_reimbursements_sync, schedule_vendor_payment_creation, \
        __validate_tax_group_mapping, check_expenses_reimbursement_status
from apps.mappings.models import GeneralMapping
from fyle_accounting_mappings.models import DestinationAttribute, EmployeeMapping, CategoryMapping
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
def test_get_or_create_credit_card_vendor_search(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value=data['search_vendor']
    )
    configuration = Configuration.objects.get(workspace_id=49)
    expense_group = ExpenseGroup.objects.filter(workspace_id=49).first()
    merchant = 'Amazon'
    auto_create_merchants = configuration.auto_create_merchants

    get_or_create_credit_card_vendor(expense_group, merchant, auto_create_merchants)
    
    created_vendor = DestinationAttribute.objects.filter(
        workspace_id=49,
        value='Amazon'
    ).first()
    
    assert created_vendor.destination_id == '1552'
    assert created_vendor.display_name == 'vendor'
    assert created_vendor.value == 'Amazon'

@pytest.mark.django_db()
def test_get_or_create_credit_card_vendor_create_true(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value={}
    )
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.post',
        return_value=data['post_vendor']
    )
    expense_group = ExpenseGroup.objects.filter(workspace_id=49).first()

    merchant = 'Random New Vendor'
    auto_create_merchants = True

    get_or_create_credit_card_vendor(expense_group, merchant, auto_create_merchants)
    
    created_vendor = DestinationAttribute.objects.filter(
        workspace_id=49,
        value='Random New Vendor'
    ).first()

    assert created_vendor.destination_id == '1000xys'
    assert created_vendor.display_name == 'vendor'
    assert created_vendor.value == 'Random New Vendor'

@pytest.mark.django_db()
def test_get_or_create_credit_card_vendor_create_false(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value={}
    )
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.post',
        return_value=data['post_vendor']
    )
    expense_group = ExpenseGroup.objects.filter(workspace_id=49).first()

    merchant = 'Random New Vendor'
    auto_create_merchants = False

    get_or_create_credit_card_vendor(expense_group, merchant, auto_create_merchants)
    
    created_vendor = DestinationAttribute.objects.filter(
        workspace_id=49,
        value='Random New Vendor'
    ).first()

    assert created_vendor == None

@pytest.mark.django_db()
def test_post_bill_success(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendor_bills.VendorBills.post',
        return_value=data['creation_response']
    )
    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    expense_group.id = 1
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)
    
    create_bill(expense_group, task_log.id)
    
    task_log = TaskLog.objects.get(pk=task_log.id)
    bill = Bill.objects.get(expense_group_id=expense_group.id)

    assert task_log.status=='COMPLETE'
    assert bill.currency == '1'
    assert bill.accounts_payable_id == '25'
    assert bill.entity_id == '12'

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_credentials.delete()

    task_log.status = 'READY'
    task_log.save()

    create_bill(expense_group, task_log.id)

    task_log = TaskLog.objects.get(id=task_log.id)
    assert task_log.detail['message'] == 'NetSuite Account not connected'


@pytest.mark.django_db()
def test_post_bill_mapping_error():
    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    CategoryMapping.objects.filter(workspace_id=1).delete()
    EmployeeMapping.objects.filter(workspace_id=1).delete()

    expense_group = ExpenseGroup.objects.get(id=2)
    create_bill(expense_group, task_log.id)

    task_log = TaskLog.objects.filter(pk=task_log.id).first()

    assert task_log.detail[0]['message'] == 'Category Mapping Not Found'
    assert task_log.status == 'FAILED'


@pytest.mark.django_db()
def test_accounting_period_working_bill(db):
    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()
    configuration = Configuration.objects.get(workspace_id=1)
    configuration.change_accounting_period = False
    configuration.save()
    expense_group.id = 1
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)

    with mock.patch('apps.netsuite.connector.NetSuiteConnector.post_bill') as mock_call:
        mock_call.side_effect = NetSuiteRequestError(message='An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.')
        create_bill(expense_group, task_log.id)

    task_log = TaskLog.objects.get(pk=task_log.id)

    assert task_log.detail[0]['message'] == 'An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'
    assert task_log.status=='FAILED'


@pytest.mark.django_db()
def test_post_expense_report(mocker, db):
    mocker.patch(
        'netsuitesdk.api.expense_reports.ExpenseReports.post',
        return_value=data['creation_response']
    )
    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    expense_group.id = 1
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)
    
    create_expense_report(expense_group, task_log.id)
    
    task_log = TaskLog.objects.get(pk=task_log.id)
    expense_report = ExpenseReport.objects.get(expense_group_id=expense_group.id)
    
    assert task_log.status=='COMPLETE'
    assert expense_report.currency == '1'
    assert expense_report.account_id == '118'
    assert expense_report.entity_id == '1676'

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_credentials.delete()

    task_log.status = 'READY'
    task_log.save()

    create_expense_report(expense_group, task_log.id)

    task_log = TaskLog.objects.get(id=task_log.id)
    assert task_log.detail['message'] == 'NetSuite Account not connected'


@pytest.mark.django_db()
def test_post_expense_report_mapping_error(db):

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
    assert task_log.status == 'FAILED'


@pytest.mark.django_db()
def test_accounting_period_working_expense_report(db):
    task_log = TaskLog.objects.filter(workspace_id=1).first()

    expense_group = ExpenseGroup.objects.get(id=2)
    expenses = expense_group.expenses.all()

    expense_group.id = random.randint(100, 1500000)
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)

    with mock.patch('apps.netsuite.connector.NetSuiteConnector.post_expense_report') as mock_call:
        mock_call.side_effect = NetSuiteRequestError(message='An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.')
        create_expense_report(expense_group, task_log.id)

    task_log = TaskLog.objects.get(pk=task_log.id)

    assert task_log.detail[0]['message'] == 'An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'
    assert task_log.status=='FAILED'


@pytest.mark.django_db()
def test_post_journal_entry(mocker, db):
    mocker.patch(
        'netsuitesdk.api.journal_entries.JournalEntries.post',
        return_value=data['creation_response']
    )
    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
    general_mappings.use_employee_class = True
    general_mappings.use_employee_department = True
    general_mappings.department_level = 'ALL'
    general_mappings.use_employee_location = True
    general_mappings.location_level = 'ALL'
    general_mappings.save()
    
    create_journal_entry(expense_group, task_log.id)

    task_log = TaskLog.objects.get(pk=task_log.id)
    journal_entry = JournalEntry.objects.get(expense_group_id=expense_group.id)

    assert task_log.status=='COMPLETE'
    assert journal_entry.currency == '1'
    assert journal_entry.external_id == 'journal 1 - ashwin.t@fyle.in'
    assert journal_entry.memo == 'Reimbursable expenses by ashwin.t@fyle.in'
    
    # journal_entry = JournalEntry.objects.get(expense_group__id=expense_group.id)
    # expense_group.id = random.randint(50, 1000)
    # expense_group.save()

    task_log.status = 'READY'
    task_log.save()

    configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)
    configuration.employee_field_mapping = 'VENDOR'
    configuration.save()

    create_journal_entry(expense_group, task_log.id)

    # journal_entry = JournalEntry.objects.get(expense_group__id=expense_group.id)
    # expense_group.id = random.randint(50, 1000)
    # expense_group.save()

    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1, fund_source='CCC').first()
    configuration.employee_field_mapping = 'EMPLOYEE'
    configuration.save()

    create_journal_entry(expense_group, task_log.id)

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_credentials.delete()

    task_log.status = 'READY'
    task_log.save()

    create_journal_entry(expense_group, task_log.id)

    task_log = TaskLog.objects.get(id=task_log.id)
    assert task_log.detail['message'] == 'NetSuite Account not connected'

@pytest.mark.django_db()
def test_post_journal_entry_mapping_error(db):

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
    assert task_log.status == 'FAILED'


@pytest.mark.django_db()
def test_accounting_period_working_create_journal_entry(db):
    task_log = TaskLog.objects.filter(workspace_id=1).first()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    expense_group.id = 1
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    with mock.patch('apps.netsuite.connector.NetSuiteConnector.post_journal_entry') as mock_call:
        mock_call.side_effect = NetSuiteRequestError(message='An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.')
        create_journal_entry(expense_group, task_log.id)

    task_log = TaskLog.objects.get(pk=task_log.id)

    assert task_log.detail[0]['message'] == 'An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'
    assert task_log.status=='FAILED'


@pytest.mark.django_db()
def test_post_credit_card_charge(mocker, db):
    class Response:
        def __init__(self, text, status_code):
            self.text = text
            self.status_code = status_code

    mocker.patch(
        'requests_oauthlib.OAuth1Session.post',
        return_value=Response(
            status_code=200,
            text=json.dumps(data['suitelet_response'])
        )
    )

    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value={}
    )

    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.post',
        return_value=data['post_vendor']
    )

    task_log = TaskLog.objects.filter(workspace_id=1).first()
    task_log.status = 'READY'
    task_log.save()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    expense_group.id = 1
    expense_group.save()

    general_mappings = GeneralMapping.objects.get(workspace_id=1)
    general_mappings.default_ccc_account_id = '10'
    general_mappings.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    expense_group.expenses.set(expenses)
    
    create_credit_card_charge(expense_group, task_log.id)
    
    task_log = TaskLog.objects.get(pk=task_log.id)
    credit_card_charge = CreditCardCharge.objects.get(expense_group_id=expense_group.id)
    
    assert task_log.status=='COMPLETE'
    assert credit_card_charge.currency == '1'
    assert credit_card_charge.credit_card_account_id == '10'
    assert credit_card_charge.external_id == 'cc-charge 1 - ashwin.t@fyle.in'

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_credentials.delete()

    task_log.status = 'READY'
    task_log.save()

    create_credit_card_charge(expense_group, task_log.id)

    task_log = TaskLog.objects.get(id=task_log.id)
    assert task_log.detail['message'] == 'NetSuite Account not connected'


@pytest.mark.django_db()
def test_post_credit_card_charge_mapping_error(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value={}
    )

    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.post',
        return_value=data['post_vendor']
    )

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

    assert task_log.detail[0]['message'] == 'Category Mapping Not Found'
    assert task_log.status == 'FAILED'


@pytest.mark.django_db()
def test_accounting_period_working_credit_card_charge(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value={}
    )

    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.post',
        return_value=data['post_vendor']
    )

    general_mappings = GeneralMapping.objects.get(workspace_id=1)
    general_mappings.default_ccc_account_id = '10'
    general_mappings.save()

    task_log = TaskLog.objects.filter(workspace_id=1).first()

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    expense_group.id = 1
    expense_group.save()

    for expense in expenses:
        expense.expense_group_id = expense_group.id
        expense.save()
    
    with mock.patch('apps.netsuite.connector.NetSuiteConnector.post_credit_card_charge') as mock_call:
        mock_call.side_effect = NetSuiteRequestError(message='An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.')
        create_credit_card_charge(expense_group, task_log.id)

    task_log = TaskLog.objects.get(pk=task_log.id)

    assert task_log.detail[0]['message'] == 'An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'
    assert task_log.status=='FAILED'


@pytest.mark.django_db()
def test_get_all_internal_ids(create_expense_report, create_task_logs):
    expense_reports = ExpenseReport.objects.all()
    internal_ids = get_all_internal_ids(expense_reports)
    
    assert internal_ids[1]['internal_id'] == 10913

@pytest.mark.django_db()
def test_check_netsuite_object_status_expense_report(create_expense_report, mocker, db):
    mocker.patch(
        'netsuitesdk.api.expense_reports.ExpenseReports.get',
        return_value=data['get_expense_report_response'][0]
    )
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    expense_report = ExpenseReport.objects.filter(expense_group__id=expense_group.id).first()
    assert expense_report.paid_on_netsuite == False

    check_netsuite_object_status(1)

    expense_report = ExpenseReport.objects.filter(expense_group__id=expense_group.id).first()
    assert expense_report.paid_on_netsuite == False


@pytest.mark.django_db()
def test_check_netsuite_object_status_bill(create_bill_task, mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendor_bills.VendorBills.get',
        return_value=data['get_bill_response'][0]
    )
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    
    bill, bill_lineitems = create_bill_task
    assert bill.paid_on_netsuite == False

    check_netsuite_object_status(1)

    bill = Bill.objects.filter(expense_group__id=expense_group.id).first()
    assert bill.paid_on_netsuite == False


def test_load_attachments(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)


    attachment = load_attachments(netsuite_connection, expense_group.expenses.first(), expense_group)
    assert attachment == None


def test_create_or_update_employee_mapping(mocker, db):
    mocker.patch(
        'netsuitesdk.api.employees.Employees.search',
        return_value={}
    )
    mocker.patch(
        'netsuitesdk.api.employees.Employees.post',
        return_value=data['post_vendor']
    )

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

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Reimbursements.sync',
        return_value=[],
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Reimbursements.list_all',
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

def test_process_vendor_payment_expense_report(mocker, db):
    mocker.patch(
        'netsuitesdk.api.expense_reports.ExpenseReports.get',
        return_value=data['get_expense_report_response'][0]
    )

    entity_object = data['entity_object']
    expense_group = ExpenseGroup.objects.get(id=1)
    entity_object['line'][0].update({
        'expense_group': expense_group
    })

    with mock.patch('apps.netsuite.connector.NetSuiteConnector.post_vendor_payment') as mock_call:
        mock_call.side_effect = NetSuiteRequestError(
            code='INVALID_KEY_OR_REF',
            message='An error occured in a upsert request: Invalid apacct reference key 223.'
        )
        process_vendor_payment(entity_object, 49, 'EXPENSE_REPORT')

    task_log = TaskLog.objects.filter(workspace_id=49, type='CREATING_VENDOR_PAYMENT').last()

    assert task_log.status == 'FAILED'

    mocker.patch(
        'netsuitesdk.api.vendor_payments.VendorPayments.post',
        return_value=data['create_vendor_payment']
    )

    process_vendor_payment(entity_object, 49, 'EXPENSE_REPORT')

    task_log = TaskLog.objects.get(workspace_id=49, type='CREATING_VENDOR_PAYMENT')
    assert task_log.status == 'COMPLETE'

    entity_object['unique_id'] = '10011023'
    expense_group.id = '12994309'
    expense_group.save()


def test_process_vendor_payment_bill(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendor_bills.VendorBills.get',
        return_value=data['get_bill_response'][0]
    )

    entity_object = data['entity_object']
    expense_group = ExpenseGroup.objects.get(id=1)
    entity_object['line'][0].update({
        'expense_group': expense_group
    })

    with mock.patch('apps.netsuite.connector.NetSuiteConnector.post_vendor_payment') as mock_call:
        mock_call.side_effect = NetSuiteRequestError(
            code='INVALID_KEY_OR_REF',
            message='An error occured in a upsert request: Invalid apacct reference key 223.'
        )
        process_vendor_payment(entity_object, 49, 'BILL')

    task_log = TaskLog.objects.filter(workspace_id=49, type='CREATING_VENDOR_PAYMENT').last()

    assert task_log.status == 'FAILED'

    mocker.patch(
        'netsuitesdk.api.vendor_payments.VendorPayments.post',
        return_value=data['create_vendor_payment']
    )

    process_vendor_payment(entity_object, 1, 'BILL')

    task_log = TaskLog.objects.get(workspace_id=1, type='CREATING_VENDOR_PAYMENT')

    assert task_log.status == 'COMPLETE'


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
