from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute
import pytest
from apps.fyle.models import ExpenseGroup
from apps.netsuite.connector import NetSuiteConnector, NetSuiteCredentials
from apps.netsuite.tasks import create_journal_entry
from tests.helper import dict_compare_keys
from .fixtures import data


def test_construct_expense_report(create_expense_report):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_report, expense_report_lineitem = create_expense_report

    expense_report = netsuite_connection._NetSuiteConnector__construct_expense_report(expense_report, expense_report_lineitem, [])

    data['expense_report_payload'][0]['tranDate'] = expense_report['tranDate']
    data['expense_report_payload'][0]['expenseList'][0]['expenseDate'] = expense_report['expenseList'][0]['expenseDate']
    assert expense_report == data['expense_report_payload'][0]


def test_construct_bill(create_bill):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    bill, bill_lineitem = create_bill
    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem, [])

    data['bill_payload'][0]['tranDate'] = bill_object['tranDate']

    assert bill_object == data['bill_payload'][0]


def test_construct_journal_entry(create_journal_entry):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    journal_entry, journal_entry_lineitem = create_journal_entry
    journal_entry_object = netsuite_connection._NetSuiteConnector__construct_journal_entry(journal_entry, journal_entry_lineitem, [])

    journal_entry_object['tranDate'] = data['journal_entry_without_single_line'][0]['tranDate']

    assert journal_entry_object == data['journal_entry_without_single_line'][0] 


def test_contruct_credit_card_charge(create_credit_card_charge):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)


    credit_card_charge, credit_card_charge_lineitem = create_credit_card_charge
    credit_card_charge_object = netsuite_connection._NetSuiteConnector__construct_credit_card_charge(credit_card_charge, credit_card_charge_lineitem, [])
    
    credit_card_charge_object['tranDate'] = data['credit_card_charge'][0]['tranDate']

    assert credit_card_charge_object == data['credit_card_charge'][0]


def test_post_vendor(add_netsuite_credentials):

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    
    vendor = netsuite_connection.post_vendor(expense_group=expense_group, merchant='Nilesh')

    assert list(vendor.items())[1][1] == '13819'
    assert list(vendor.items())[2][1] == 'Nilesh'

def test_get_bill(add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    bill = netsuite_connection.get_bill(238)
    
    assert dict_compare_keys(bill, data['get_bill_response'][0]) == [], 'get bill api return diffs in keys'


def test_get_expense_report(add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_report = netsuite_connection.get_expense_report(85327)
    assert dict_compare_keys(expense_report, data['get_expense_report_response'][0]) == [], 'get expense report returns diff in keys'


def test_sync_project(add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert project_count == 1086

    netsuite_connection.sync_projects()

    new_project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert new_project_count == 1088

def test_sync_employee(add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    employee_count = DestinationAttribute.objects.filter(workspace_id=49, attribute_type='EMPLOYEE').count()
    assert employee_count == 12

    netsuite_connection.sync_employees()

    new_employee_count = DestinationAttribute.objects.filter(workspace_id=49, attribute_type='EMPLOYEE').count()
    assert new_employee_count == 14

@pytest.mark.django_db()
def test_sync_accounts(add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    accounts_count = DestinationAttribute.objects.filter(attribute_type='ACCOUNT', workspace_id=1).count()
    assert accounts_count == 123

    netsuite_connection.sync_accounts()

    new_account_counts = DestinationAttribute.objects.filter(attribute_type='ACCOUNT', workspace_id=1).count()
    assert new_account_counts == 164

@pytest.mark.django_db()
def test_sync_expense_categories(add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_categories_count = DestinationAttribute.objects.filter(attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert expense_categories_count == 33

    netsuite_connection.sync_expense_categories()

    new_expense_categories_count = DestinationAttribute.objects.filter(attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert new_expense_categories_count == 38


@pytest.mark.django_db()
def test_sync_custom_segments(db, add_netsuite_credentials, add_custom_segment):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    custom_record = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_BANDS', workspace_id=49).count()
    assert custom_record == 5
    custom_list = DestinationAttribute.objects.filter(attribute_type='SRAVAN_DEMO', workspace_id=49).count()
    assert custom_list == 2

    custom_segment = DestinationAttribute.objects.filter(attribute_type='PRODUCTION_LINE', workspace_id=49).count()
    assert custom_segment == 2

    netsuite_connection.sync_custom_segments()

    custom_record = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_BANDS', workspace_id=49).count()
    assert custom_record == 5
    custom_list = DestinationAttribute.objects.filter(attribute_type='SRAVAN_DEMO', workspace_id=49).count()
    assert custom_list == 2
    custom_segment = DestinationAttribute.objects.filter(attribute_type='PRODUCTION_LINE', workspace_id=49).count()
    assert custom_segment == 2


def test_sync_subsidiaries(db, add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    subsidiaries = DestinationAttribute.objects.filter(attribute_type='SUBSIDIARY', workspace_id=49).count()
    assert subsidiaries == 7

    netsuite_connection.sync_subsidiaries()

    subsidiaries = DestinationAttribute.objects.filter(attribute_type='SUBSIDIARY', workspace_id=49).count()
    assert subsidiaries == 10


def test_get_or_create_vendor(db, add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    source_employee = ExpenseAttribute.objects.get(
        workspace_id=expense_group.workspace_id,
        attribute_type='EMPLOYEE',
        value=expense_group.description.get('employee_email')
    )
    vendor = DestinationAttribute.objects.filter(attribute_type='VENDOR', workspace_id=1).count()
    assert vendor == 3

    netsuite_connection.get_or_create_vendor(source_employee, expense_group)

    vendor = DestinationAttribute.objects.filter(attribute_type='VENDOR', workspace_id=1).count()
    assert vendor == 3
