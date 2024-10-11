import pytest
from datetime import datetime
from unittest import mock
from apps.fyle.models import ExpenseGroup
from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute, Mapping, CategoryMapping
from apps.netsuite.connector import NetSuiteConnector, NetSuiteCredentials
from apps.workspaces.models import Configuration, Workspace
from netsuitesdk import NetSuiteRequestError
from tests.helper import dict_compare_keys
from .fixtures import data
import logging

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def test_construct_expense_report(create_expense_report):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_report, expense_report_lineitem = create_expense_report

    expense_report = netsuite_connection._NetSuiteConnector__construct_expense_report(expense_report, expense_report_lineitem)

    data['expense_report_payload'][0]['tranDate'] = expense_report['tranDate']
    data['expense_report_payload'][0]['expenseList'][0]['expenseDate'] = expense_report['expenseList'][0]['expenseDate']
    assert expense_report == data['expense_report_payload'][0]


def test_construct_bill_account_based(create_bill_account_based):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    bill, bill_lineitem = create_bill_account_based
    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem)

    data['bill_payload_account_based'][0]['tranDate'] = bill_object['tranDate']
    data['bill_payload_account_based'][0]['tranId'] = bill_object['tranId']

    assert data['bill_payload_account_based'][0]['itemList'] == None
    assert dict_compare_keys(bill_object, data['bill_payload_account_based'][0]) == [], 'construct bill_payload entry api return diffs in keys'

def test_construct_bill_item_based(create_bill_item_based):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    bill, bill_lineitem = create_bill_item_based
    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem)

    assert data['bill_payload_item_based']['expenseList'] == None
    assert dict_compare_keys(bill_object, data['bill_payload_item_based']) == [], 'construct bill_payload entry api return diffs in keys'


def test_construct_bill_item_and_account_based(create_bill_item_and_account_based):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    bill, bill_lineitem = create_bill_item_and_account_based
    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem)

    assert dict_compare_keys(bill_object, data['bill_payload_item_and_account_based']) == [], 'construct bill_payload entry api return diffs in keys'


def test_construct_journal_entry(create_journal_entry):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    configuration = Configuration.objects.get(workspace_id=1)

    journal_entry, journal_entry_lineitem = create_journal_entry
    journal_entry_object = netsuite_connection._NetSuiteConnector__construct_journal_entry(journal_entry, journal_entry_lineitem, configuration)

    journal_entry_object['tranDate'] = data['journal_entry_without_single_line'][0]['tranDate']

    assert journal_entry_object == data['journal_entry_without_single_line'][0] 


def test_contruct_credit_card_charge(create_credit_card_charge):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)


    credit_card_charge, credit_card_charge_lineitem = create_credit_card_charge
    credit_card_charge_object = netsuite_connection._NetSuiteConnector__construct_credit_card_charge(credit_card_charge, credit_card_charge_lineitem, [])
    
    credit_card_charge_object['tranDate'] = data['credit_card_charge'][0]['tranDate']
    credit_card_charge_object['tranid'] = data['credit_card_charge'][0]['tranid']

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

    with mock.patch('netsuitesdk.api.vendors.Vendors.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError({
            'message': {'isperson': True}
        }), None]
        netsuite_connection.post_vendor(expense_group=expense_group, merchant='Nilesh')
    

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
        'netsuitesdk.api.vendors.Vendors.count',
        return_value=0
    )
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
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get',
        return_value=data['get_all_employees'][0][0]
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
        'netsuitesdk.api.accounts.Accounts.count',
        return_value=5 
    )
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
def test_sync_items(mocker, db):
    with mock.patch('netsuitesdk.api.items.Items.get_all_generator') as mock_call:
        # here we have the import_items set to false , So none of the destination attributes should be active
        configuration = Configuration.objects.get(workspace_id=1)
        configuration.import_items = False
        configuration.save()

        mock_call.return_value = data['get_all_items']

        netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
        netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

        items_count = DestinationAttribute.objects.filter(attribute_type='ACCOUNT',display_name='Item', workspace_id=1).count()
        assert items_count == 0

        netsuite_connection.sync_items()

        new_items_count = DestinationAttribute.objects.filter(attribute_type='ACCOUNT',display_name='Item', workspace_id=1, active= True).count()
        assert new_items_count == 0

        # here we have the import_items set to true, So all the destination attributes will be set to state present in netsuite
        configuration = Configuration.objects.get(workspace_id=1)
        configuration.import_items = True
        configuration.save()
        mock_call.return_value = data['get_all_items']

        netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
        netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

        netsuite_connection.sync_items()

        new_items_count = DestinationAttribute.objects.filter(attribute_type='ACCOUNT',display_name='Item', workspace_id=1, active= True).count()
        assert new_items_count == 3

        mock_call.return_value = data['get_all_items_with_inactive_values']

        netsuite_connection.sync_items()

        new_items_count = DestinationAttribute.objects.filter(attribute_type='ACCOUNT',display_name='Item', workspace_id=1, active= True).count()
        assert new_items_count == 2


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
    assert custom_record == 0
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
        'netsuitesdk.api.locations.Locations.count',
        return_value=5
    )
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
    assert locations == 12


def test_sync_departments(mocker, db):
    mocker.patch(
        'netsuitesdk.api.departments.Departments.count',
        return_value=5
    )
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
    assert tax_items == 32


def test_sync_currencies(mocker, db):
    mocker.patch(
        'netsuitesdk.api.currencies.Currencies.get_all_generator',
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
        'netsuitesdk.api.classifications.Classifications.count',
        return_value=5
    )
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

    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value=None
    )
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.post',
        return_value=data['post_vendor']
    )
    netsuite_connection.get_or_create_vendor(source_employee, expense_group)

    vendors = DestinationAttribute.objects.filter(attribute_type='VENDOR', workspace_id=1).count()
    assert vendors == 5


def test_get_or_create_employee(mocker, db):
    mocker.patch(
        'netsuitesdk.api.employees.Employees.search',
        return_value=data['get_all_employees'][0]
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    source_employee = ExpenseAttribute.objects.get(
        workspace_id=expense_group.workspace_id,
        attribute_type='EMPLOYEE',
        value=expense_group.description.get('employee_email')
    )
    employees = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1).count()
    assert employees == 7

    netsuite_connection.get_or_create_employee(source_employee, expense_group)

    employees = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1).count()
    assert employees == 8

    mocker.patch(
        'netsuitesdk.api.employees.Employees.search',
        return_value=None
    )
    mocker.patch(
        'netsuitesdk.api.employees.Employees.post',
        return_value={
            'internalId': 'dfghjk'
        }
    )
    netsuite_connection.get_or_create_employee(source_employee, expense_group)

    employees = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1).count()
    assert employees == 9


def test_post_employee(mocker, db):
    mocker.patch(
        'netsuitesdk.api.employees.Employees.post',
        return_value=data['get_all_employees'][0]
    )
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    employee_attribute = ExpenseAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1).first()
    
    vendor = netsuite_connection.post_employee(expense_group=expense_group, employee=employee_attribute)

    assert dict_compare_keys(vendor, data['post_vendor']) == [], 'post vendor api return diffs in keys'


def test_post_credit_card_charge_exception(db, mocker, create_credit_card_charge):
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    credit_card_charge_transaction, credit_card_charge_transaction_lineitems = create_credit_card_charge

    workspace_general_setting = Configuration.objects.get(workspace_id=workspace_id)
    workspace_general_setting.change_accounting_period = True
    workspace_general_setting.save()

    try:
        mocker.patch(
            'requests_oauthlib.OAuth1Session.post',
            return_value=mock.MagicMock(status_code=400, text="{'error': {'message': json.dumps({'message': 'The transaction date you specified is not within the date range of your accounting period.'}), 'code': 400}}")
        )
        netsuite_connection.post_credit_card_charge(credit_card_charge_transaction, credit_card_charge_transaction_lineitems, {}, True)
    except:
        logger.info('accounting period error')


def test_post_credit_card_charge_bad_ns_response(db, mocker, create_credit_card_charge):
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    credit_card_charge_transaction, credit_card_charge_transaction_lineitems = create_credit_card_charge

    workspace_general_setting = Configuration.objects.get(workspace_id=workspace_id)
    workspace_general_setting.change_accounting_period = True
    workspace_general_setting.save()

    try:
        mocker.patch(
            'requests_oauthlib.OAuth1Session.post',
            return_value=mock.MagicMock(status_code=400, text="""{"code" : "UNABLE_TO_SAVE_THE_TRANSACTION_DUE_TO_AN_ERROR_BEING_REPORTED_BY_THE_TAX_CALCULATION_ENGINE_1", "message" : "{\\"type\\":\\"error.SuiteScriptError\\",\\"name\\":\\"UNABLE_TO_SAVE_THE_TRANSACTION_DUE_TO_AN_ERROR_BEING_REPORTED_BY_THE_TAX_CALCULATION_ENGINE_1\\",\\"message\\":\\"Unable to save the transaction due to an error being reported by the tax calculation engine: Tax Calculation Plugin error: NetSuite was not able to estimate the correct Nexus for this transaction. Based on the <a href=\\\\"https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4283866360.html\\\\">Nexus Determination Lookup Logic in SuiteTax</a>, NetSuite has determined the Ship From country United States, Ship To country United States and the Subsidiary country United States, these countries do not match any Subsidiary Tax Registration. You must have an active nexus that matches one of the countries identified in the nexus lookup logic. If you want taxes to be calculated for the nexus, set up the nexus and assign a tax engine. Otherwise, mark the nexus as tax-exempt. Go to the <a href=\\\'/app/common/otherlists/subsidiarytype.nl?id=1\\\'>subsidiary</a> to complete the setup. You may need to contact your administrator to perform this action.\\",\\"stack\\":[\\"anonymous(N/serverRecordService)\\",\\"CreateNetSuiteCreditCardCharge(/SuiteBundles/Bundle 355595/create_credit_card_charge.js:122)\\",\\"doPost(/SuiteBundles/Bundle 355595/create_credit_card_charge.js:23)\\"],\\"cause\\":{\\"type\\":\\"internal error\\",\\"code\\":\\"UNABLE_TO_SAVE_THE_TRANSACTION_DUE_TO_AN_ERROR_BEING_REPORTED_BY_THE_TAX_CALCULATION_ENGINE_1\\",\\"details\\":\\"Unable to save the transaction due to an error being reported by the tax calculation engine: Tax Calculation Plugin error: NetSuite was not able to estimate the correct Nexus for this transaction. Based on the <a href=\\\\"https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4283866360.html\\\\">Nexus Determination Lookup Logic in SuiteTax</a>, NetSuite has determined the Ship From country United States, Ship To country United States and the Subsidiary country United States, these countries do not match any Subsidiary Tax Registration. You must have an active nexus that matches one of the countries identified in the nexus lookup logic. If you want taxes to be calculated for the nexus, set up the nexus and assign a tax engine. Otherwise, mark the nexus as tax-exempt. Go to the <a href=\\\'/app/common/otherlists/subsidiarytype.nl?id=1\\\'>subsidiary</a> to complete the setup. You may need to contact your administrator to perform this action.\\",\\"userEvent\\":null,\\"stackTrace\\":[\\"anonymous(N/serverRecordService)\\",\\"CreateNetSuiteCreditCardCharge(/SuiteBundles/Bundle 355595/create_credit_card_charge.js:122)\\",\\"doPost(/SuiteBundles/Bundle 355595/create_credit_card_charge.js:23)\\"],\\"notifyOff\\":false},\\"id\\":\\"\\",\\"notifyOff\\":false,\\"userFacing\\":false}"}""")
        )
        netsuite_connection.post_credit_card_charge(credit_card_charge_transaction, credit_card_charge_transaction_lineitems, {}, True)
    except:
        logger.info('accounting period error')


def test_post_bill_exception(db, mocker, create_bill_account_based):
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    bill_transaction, bill_transaction_lineitems = create_bill_account_based

    workspace_general_setting = Configuration.objects.get(workspace_id=workspace_id)
    workspace_general_setting.change_accounting_period = True
    workspace_general_setting.save()

    with mock.patch('netsuitesdk.api.vendor_bills.VendorBills.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError('An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'), None]
        netsuite_connection.post_bill(bill_transaction, bill_transaction_lineitems)


def test_post_expense_report_exception(db, mocker, create_expense_report):
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    expense_report_transaction, expense_report_transaction_lineitems = create_expense_report

    workspace_general_setting = Configuration.objects.get(workspace_id=workspace_id)
    workspace_general_setting.change_accounting_period = True
    workspace_general_setting.save()

    with mock.patch('netsuitesdk.api.expense_reports.ExpenseReports.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError('An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'), None]
        netsuite_connection.post_expense_report(expense_report_transaction, expense_report_transaction_lineitems)


def test_post_journal_entry_exception(db, mocker, create_journal_entry):
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    journal_entry_transaction, journal_entry_transaction_lineitems = create_journal_entry

    configuration = Configuration.objects.get(workspace_id=workspace_id)

    workspace_general_setting = Configuration.objects.get(workspace_id=workspace_id)
    workspace_general_setting.change_accounting_period = True
    workspace_general_setting.save()

    with mock.patch('netsuitesdk.api.journal_entries.JournalEntries.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError('An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'), None]
        netsuite_connection.post_journal_entry(journal_entry_transaction, journal_entry_transaction_lineitems, configuration)

def test_update_destination_attributes(db, mocker):
    mocker.patch(
        'netsuitesdk.api.custom_record_types.CustomRecordTypes.get_all_by_id',
        return_value=data['custom_records']
    )

    custom_segments = data['custom_segment_destination_attributes']
    custom_segments_destination_attribute = []
    for custom_segment in custom_segments:
        workspace_id = custom_segment.pop('workspace_id')
        workspace = Workspace.objects.get(id=workspace_id)
        custom_segments_destination_attribute.append(
            DestinationAttribute(
                **custom_segment,
                workspace=workspace
            )
        )
    DestinationAttribute.objects.bulk_create(custom_segments_destination_attribute, batch_size=50)
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    custom_records = netsuite_connection.connection.custom_record_types.get_all_by_id('1')
    netsuite_connection.update_destination_attributes('CUSTOM_TYPE', custom_records)

    custom_type_destination_attributes = DestinationAttribute.objects.filter(attribute_type='CUSTOM_TYPE', workspace_id=1)

    for custom_type_destination_attribute in custom_type_destination_attributes:
        if custom_type_destination_attribute.value == 'Type B':
           assert custom_type_destination_attribute.destination_id == '22'
        elif custom_type_destination_attribute.value == 'Type C':
            assert custom_type_destination_attribute.destination_id == '33'
        elif custom_type_destination_attribute.value == 'Type A':
           assert custom_type_destination_attribute.destination_id == '1'
        elif custom_type_destination_attribute.value == 'Type D':
           assert custom_type_destination_attribute.destination_id == '4'


def test_skip_sync_attributes(mocker, db):
    mocker.patch(
        'netsuitesdk.api.projects.Projects.count',
        return_value=10001
    )

    mocker.patch(
        'netsuitesdk.api.classifications.Classifications.count',
        return_value=2001
    )
    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.count',
        return_value=2001
    )
    mocker.patch(
        'netsuitesdk.api.locations.Locations.count',
        return_value=2001
    )
    mocker.patch(
        'netsuitesdk.api.departments.Departments.count',
        return_value=2001
    )
    mocker.patch(
        'netsuitesdk.api.customers.Customers.count',
        return_value=25001
    )
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.count',
        return_value=20001
    )

    today = datetime.today()
    Workspace.objects.filter(id=1).update(created_at=today)
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    Mapping.objects.filter(workspace_id=1).delete()
    CategoryMapping.objects.filter(workspace_id=1).delete()

    DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').delete()

    netsuite_connection.sync_projects()

    new_project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert new_project_count == 0

    DestinationAttribute.objects.filter(workspace_id=1, attribute_type='CLASS').delete()

    netsuite_connection.sync_classifications()

    classifications = DestinationAttribute.objects.filter(attribute_type='CLASS', workspace_id=1).count()
    assert classifications == 0

    DestinationAttribute.objects.filter(workspace_id=1, attribute_type='ACCOUNT').delete()

    netsuite_connection.sync_accounts()

    new_project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='ACCOUNT').count()
    assert new_project_count == 0

    DestinationAttribute.objects.filter(workspace_id=1, attribute_type='LOCATION').delete()

    netsuite_connection.sync_locations()

    new_project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='LOCATION').count()
    assert new_project_count == 0

    DestinationAttribute.objects.filter(workspace_id=1, attribute_type='DEPARTMENT').delete()

    netsuite_connection.sync_departments()

    new_project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='DEPARTMENT').count()
    assert new_project_count == 0

    DestinationAttribute.objects.filter(workspace_id=1, attribute_type='CUSTOMER').delete()

    netsuite_connection.sync_customers()

    new_project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='CUSTOMER').count()
    assert new_project_count == 0
    