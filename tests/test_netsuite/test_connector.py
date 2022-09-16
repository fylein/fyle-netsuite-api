from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute
import pytest
from apps.fyle.models import ExpenseGroup
from apps.netsuite.connector import NetSuiteConnector, NetSuiteCredentials
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


def test_post_vendor(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.post',
        return_value=data['post_vendor']
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    
    vendor = netsuite_connection.post_vendor(expense_group=expense_group, merchant='Nilesh')

    assert dict_compare_keys(vendor, data['post_vendor']) == [], 'post vendor api return diffs in keys'

def test_get_bill(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendor_bills.VendorBills.get',
        return_value=data['get_bill_response'][0]
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    bill = netsuite_connection.get_bill(238)
    
    assert dict_compare_keys(bill, data['get_bill_response'][0]) == [], 'get bill api return diffs in keys'


def test_get_expense_report(mocker, db):
    mocker.patch(
        'netsuitesdk.api.expense_reports.ExpenseReports.get',
        return_value=data['get_expense_report_response'][0]   
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_report = netsuite_connection.get_expense_report(85327)
    assert dict_compare_keys(expense_report, data['get_expense_report_response'][0]) == [], 'get expense report returns diff in keys'

def test_sync_vendors(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.get_all_generator',
        return_value=data['get_all_vendors']    
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    vendors_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='VENDOR').count()
    assert vendors_count == 3

    netsuite_connection.sync_vendors()

    new_vendors_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='VENDOR').count()
    assert new_vendors_count == 7


def test_sync_projects(mocker, db):
    mocker.patch(
        'netsuitesdk.api.projects.Projects.get_all_generator',
        return_value=data['get_all_projects']    
    )

    mocker.patch(
        'netsuitesdk.api.projects.Projects.count',
        return_value=len(data['get_all_projects'][0])
    )

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert project_count == 1086

    netsuite_connection.sync_projects()

    new_project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert new_project_count == 1087

def test_sync_employees(mocker, db):
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=data['get_all_employees']    
    )

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    employee_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='EMPLOYEE').count()
    assert employee_count == 7

    netsuite_connection.sync_employees()

    new_employee_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='EMPLOYEE').count()
    assert new_employee_count == 13

@pytest.mark.django_db()
def test_sync_accounts(mocker, db):
    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.get_all_generator',
        return_value=data['get_all_accounts']    
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    accounts_count = DestinationAttribute.objects.filter(attribute_type='ACCOUNT', workspace_id=1).count()
    assert accounts_count == 123

    netsuite_connection.sync_accounts()

    new_account_counts = DestinationAttribute.objects.filter(attribute_type='ACCOUNT', workspace_id=1).count()
    assert new_account_counts == 124

@pytest.mark.django_db()
def test_sync_expense_categories(mocker, db):
    mocker.patch(
        'netsuitesdk.api.expense_categories.ExpenseCategory.get_all_generator',
        return_value=data['get_all_expense_categories']
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_categories_count = DestinationAttribute.objects.filter(attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert expense_categories_count == 33

    netsuite_connection.sync_expense_categories()

    new_expense_categories_count = DestinationAttribute.objects.filter(attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert new_expense_categories_count == 34


@pytest.mark.django_db()
def test_sync_custom_segments(mocker, db):
    mocker.patch(
        'netsuitesdk.api.custom_segments.CustomSegments.get',
        return_value=data['get_custom_segment']
    )

    mocker.patch(
        'netsuitesdk.api.custom_record_types.CustomRecordTypes.get_all_by_id',
        return_value=data['get_custom_records_all']
    )

    mocker.patch(
        'netsuitesdk.api.custom_lists.CustomLists.get',
        return_value=data['get_custom_list']
    )
    
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    custom_record = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_BANDS', workspace_id=49)
    assert custom_record.count() == 0
    custom_list = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_SINGER', workspace_id=49)
    assert custom_list.count() == 0

    custom_segment = DestinationAttribute.objects.filter(attribute_type='PRODUCTION_LINE', workspace_id=49)
    assert custom_segment.count() == 0

    netsuite_connection.sync_custom_segments()

    custom_record = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_BANDS', workspace_id=49).count()
    assert custom_record == 5
    custom_list = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_SINGER', workspace_id=49).count()
    assert custom_list == 6
    custom_segment = DestinationAttribute.objects.filter(attribute_type='PRODUCTION_LINE', workspace_id=49).count()
    assert custom_segment == 5


def test_sync_subsidiaries(mocker, db):
    mocker.patch(
        'netsuitesdk.api.subsidiaries.Subsidiaries.get_all_generator',
        return_value=data['get_all_subsidiaries']
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    subsidiaries = DestinationAttribute.objects.filter(attribute_type='SUBSIDIARY', workspace_id=49).count()
    assert subsidiaries == 7

    netsuite_connection.sync_subsidiaries()

    subsidiaries = DestinationAttribute.objects.filter(attribute_type='SUBSIDIARY', workspace_id=49).count()
    assert subsidiaries == 8

def test_sync_locations(mocker, db):
    mocker.patch(
        'netsuitesdk.api.locations.Locations.get_all_generator',
        return_value=data['get_all_locations']
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    locations = DestinationAttribute.objects.filter(attribute_type='LOCATION', workspace_id=49).count()
    assert locations == 12

    netsuite_connection.sync_locations()

    locations = DestinationAttribute.objects.filter(attribute_type='LOCATION', workspace_id=49).count()
    assert locations == 13


def test_sync_departments(mocker, db):
    mocker.patch(
        'netsuitesdk.api.departments.Departments.get_all_generator',
        return_value=data['get_all_departments']
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    departments = DestinationAttribute.objects.filter(attribute_type='DEPARTMENT', workspace_id=49).count()
    assert departments == 12

    netsuite_connection.sync_departments()

    departments = DestinationAttribute.objects.filter(attribute_type='DEPARTMENT', workspace_id=49).count()
    assert departments == 13


def test_sync_customers(mocker, db):
    mocker.patch(
        'netsuitesdk.api.customers.Customers.get_all_generator',
        return_value=data['get_all_projects']    
    )

    mocker.patch(
        'netsuitesdk.api.customers.Customers.count',
        return_value=len(data['get_all_projects'][0])
    )

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    customers = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert customers == 1086

    netsuite_connection.sync_customers()

    customers = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert customers == 1087


def test_sync_tax_items(mocker, db):
    mocker.patch(
        'netsuitesdk.api.tax_items.TaxItems.get_all_generator',
        return_value=data['get_all_tax_items']    
    )

    mocker.patch(
        'netsuitesdk.api.tax_groups.TaxGroups.get_all_generator',
        return_value=data['get_all_tax_groups']
    )

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    tax_items = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='TAX_ITEM').count()
    assert tax_items == 26

    netsuite_connection.sync_tax_items()

    tax_items = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='TAX_ITEM').count()
    assert tax_items == 31


def test_sync_currencies(mocker, db):
    mocker.patch(
        'netsuitesdk.api.currencies.Currencies.get_all',
        return_value=data['get_all_currencies'][0]
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    currencies = DestinationAttribute.objects.filter(attribute_type='CURRENCY', workspace_id=49).count()
    assert currencies == 6

    netsuite_connection.sync_currencies()

    currencies = DestinationAttribute.objects.filter(attribute_type='CURRENCY', workspace_id=49).count()
    assert currencies == 7


def test_sync_classifications(mocker, db):
    mocker.patch(
        'netsuitesdk.api.classifications.Classifications.get_all_generator',
        return_value=data['get_all_classifications']
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    classifications = DestinationAttribute.objects.filter(attribute_type='CLASS', workspace_id=49).count()
    assert classifications == 18

    netsuite_connection.sync_classifications()

    classifications = DestinationAttribute.objects.filter(attribute_type='CLASS', workspace_id=49).count()
    assert classifications == 19


def test_get_or_create_vendor(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value=data['search_vendor']
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    source_employee = ExpenseAttribute.objects.get(
        workspace_id=expense_group.workspace_id,
        attribute_type='EMPLOYEE',
        value=expense_group.description.get('employee_email')
    )
    vendors = DestinationAttribute.objects.filter(attribute_type='VENDOR', workspace_id=1).count()
    assert vendors == 3

    netsuite_connection.get_or_create_vendor(source_employee, expense_group)

    vendors = DestinationAttribute.objects.filter(attribute_type='VENDOR', workspace_id=1).count()
    assert vendors == 4
