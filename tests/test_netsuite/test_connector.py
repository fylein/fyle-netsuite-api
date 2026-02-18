import pytest
from copy import deepcopy
from datetime import datetime
from unittest import mock
from django.utils import timezone
from apps.fyle.models import ExpenseGroup
from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute, Mapping, CategoryMapping
from apps.netsuite.connector import NetSuiteConnector, NetSuiteCredentials
from apps.workspaces.models import Configuration, Workspace, FeatureConfig
from apps.mappings.models import GeneralMapping
from netsuitesdk import NetSuiteRequestError
from tests.helper import dict_compare_keys
from .fixtures import data
import logging

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def test_construct_expense_report(create_expense_report):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    feature_config = FeatureConfig.objects.get(workspace_id=1)

    expense_report, expense_report_lineitem = create_expense_report

    expense_report = netsuite_connection._NetSuiteConnector__construct_expense_report(expense_report, expense_report_lineitem, general_mapping)

    data['expense_report_payload'][0]['tranDate'] = expense_report['tranDate']
    data['expense_report_payload'][0]['expenseList'][0]['expenseDate'] = expense_report['expenseList'][0]['expenseDate']
    assert expense_report == data['expense_report_payload'][0]

def test_construct_expense_report_with_tax_balancing(create_expense_report, add_tax_destination_attributes):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    feature_config = FeatureConfig.objects.get(workspace_id=1)
    # without tax balancing
    expense_report, expense_report_lineitem = create_expense_report
    expense_report_lineitem[0].amount = 100
    expense_report_lineitem[0].tax_amount = 3
    expense_report_lineitem[0].tax_item_id = '103578'

    expense_report_object = netsuite_connection._NetSuiteConnector__construct_expense_report(expense_report, expense_report_lineitem, general_mapping)

    assert len(expense_report_object['expenseList']) == 1
    assert expense_report_object['expenseList'][0]['amount'] == 97
    assert expense_report_object['expenseList'][0]['taxCode']['internalId'] == '103578'
    assert expense_report_object['expenseList'][0]['tax1Amt'] == 3

    # with tax balancing
    general_mapping.is_tax_balancing_enabled = True
    general_mapping.save()

    expense_report_object = netsuite_connection._NetSuiteConnector__construct_expense_report(expense_report, expense_report_lineitem, general_mapping)

    assert len(expense_report_object['expenseList']) == 2
    assert expense_report_object['expenseList'][0]['amount'] == 60
    assert expense_report_object['expenseList'][0]['taxCode']['internalId'] == '103578'
    assert expense_report_object['expenseList'][0]['tax1Amt'] == 3
    assert expense_report_object['expenseList'][1]['amount'] == 37
    assert expense_report_object['expenseList'][1]['taxCode']['internalId'] == general_mapping.default_tax_code_id


    # with tax balancing enabled and right tax amount
    expense_report_lineitem[0].amount = 100
    expense_report_lineitem[0].tax_amount = 4.76
    expense_report_lineitem[0].tax_item_id = '103578'

    expense_report_object = netsuite_connection._NetSuiteConnector__construct_expense_report(expense_report, expense_report_lineitem, general_mapping)

    assert len(expense_report_object['expenseList']) == 1
    assert expense_report_object['expenseList'][0]['amount'] == 95.24
    assert expense_report_object['expenseList'][0]['taxCode']['internalId'] == '103578'
    assert expense_report_object['expenseList'][0]['tax1Amt'] == 4.76

    general_mapping.is_tax_balancing_enabled = False
    general_mapping.save()

def test_construct_bill_account_based(create_bill_account_based):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    feature_config = FeatureConfig.objects.get(workspace_id=1)

    bill, bill_lineitem = create_bill_account_based
    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem, general_mapping)

    data['bill_payload_account_based'][0]['tranDate'] = bill_object['tranDate']
    data['bill_payload_account_based'][0]['tranId'] = bill_object['tranId']

    assert data['bill_payload_account_based'][0]['itemList'] == None
    assert dict_compare_keys(bill_object, data['bill_payload_account_based'][0]) == [], 'construct bill_payload entry api return diffs in keys'

def test_construct_bill_item_based(create_bill_item_based):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    feature_config = FeatureConfig.objects.get(workspace_id=1)

    bill, bill_lineitem = create_bill_item_based
    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem, general_mapping)

    assert data['bill_payload_item_based']['expenseList'] == None
    assert dict_compare_keys(bill_object, data['bill_payload_item_based']) == [], 'construct bill_payload entry api return diffs in keys'


def test_construct_bill_item_and_account_based(create_bill_item_and_account_based):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    feature_config = FeatureConfig.objects.get(workspace_id=1)

    bill, bill_lineitem = create_bill_item_and_account_based
    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem, general_mapping)

    assert dict_compare_keys(bill_object, data['bill_payload_item_and_account_based']) == [], 'construct bill_payload entry api return diffs in keys'

def test_construct_bill_item_for_tax_balancing(create_bill_account_based, add_tax_destination_attributes):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    feature_config = FeatureConfig.objects.get(workspace_id=1)

    # without tax balancing
    bill, bill_lineitem = create_bill_account_based
    bill_lineitem[0].amount = 100
    bill_lineitem[0].tax_amount = 3
    bill_lineitem[0].tax_item_id = '103578'

    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem, general_mapping)

    assert len(bill_object['expenseList']) == 1
    assert bill_object['expenseList'][0]['amount'] == 97
    assert bill_object['expenseList'][0]['taxCode']['internalId'] == '103578'
    assert dict_compare_keys(bill_object, data['bill_payload_account_based'][0]) == [], 'construct bill_payload entry api return diffs in keys'

    # with tax balancing
    general_mapping.is_tax_balancing_enabled = True
    general_mapping.save()

    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem, general_mapping)
    assert len(bill_object['expenseList']) == 2
    assert bill_object['expenseList'][0]['amount'] == 60
    assert bill_object['expenseList'][0]['taxCode']['internalId'] == '103578'
    assert bill_object['expenseList'][1]['amount'] == 37
    assert bill_object['expenseList'][1]['taxCode']['internalId'] == general_mapping.default_tax_code_id

    # with tax balancing enabled and right tax amount
    bill_lineitem[0].amount = 100
    bill_lineitem[0].tax_amount = 4.76
    bill_lineitem[0].tax_item_id = '103578'

    bill_object = netsuite_connection._NetSuiteConnector__construct_bill(bill, bill_lineitem, general_mapping)
    assert len(bill_object['expenseList']) == 1
    assert bill_object['expenseList'][0]['amount'] == 95.24
    assert bill_object['expenseList'][0]['taxCode']['internalId'] == '103578'

    general_mapping.is_tax_balancing_enabled = False
    general_mapping.save()


def test_construct_journal_entry(create_journal_entry):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    configuration = Configuration.objects.get(workspace_id=1)
    general_mapping = GeneralMapping.objects.get(workspace_id=1)

    journal_entry, journal_entry_lineitem = create_journal_entry
    journal_entry_object = netsuite_connection._NetSuiteConnector__construct_journal_entry(journal_entry, journal_entry_lineitem, configuration, general_mapping)

    journal_entry_object['tranDate'] = data['journal_entry_without_single_line'][0]['tranDate']

    assert journal_entry_object == data['journal_entry_without_single_line'][0]

    configuration.je_single_credit_line = True
    configuration.save()

    journal_entry_object = netsuite_connection._NetSuiteConnector__construct_journal_entry(journal_entry, journal_entry_lineitem, configuration, general_mapping)

    # With flag being different, the output should be different
    assert journal_entry_object != data['journal_entry_without_single_line'][0] 


def test_construct_single_itemized_credit_line(create_journal_entry):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(
        netsuite_credentials=netsuite_credentials, workspace_id=1
    )

    _, journal_entry_lineitems = create_journal_entry

    # Single line item
    constructed_lines = netsuite_connection._NetSuiteConnector__construct_single_itemized_credit_line(
        journal_entry_lineitems
    )
    assert constructed_lines == data['journal_entry_clubbed_lines']

    # Double line item with same ids
    journal_entry_lineitems_2 = journal_entry_lineitems.copy() + journal_entry_lineitems.copy()
    constructed_lines = netsuite_connection._NetSuiteConnector__construct_single_itemized_credit_line(
        journal_entry_lineitems_2
    )

    expected_lines = deepcopy(data['journal_entry_clubbed_lines'][0])
    expected_lines['credit'] = 2 * expected_lines['credit']
    expected_lines = [expected_lines]

    assert constructed_lines == expected_lines

    # Multiple line items with different ids
    journal_entry_lineitems_3 = []
    for i in range(4):
        instance = deepcopy(journal_entry_lineitems[0])
        instance.id = None
        journal_entry_lineitems_3.append(instance)

    journal_entry_lineitems_3[1].entity_id = '111'
    journal_entry_lineitems_3[2].debit_account_id = '222'

    constructed_lines = netsuite_connection._NetSuiteConnector__construct_single_itemized_credit_line(
        journal_entry_lineitems_3
    )

    line_1 = deepcopy(data['journal_entry_clubbed_lines'][0])
    line_2 = deepcopy(data['journal_entry_clubbed_lines'][0])
    line_3 = deepcopy(data['journal_entry_clubbed_lines'][0])

    line_2['entity']['internalId'] = '111'
    line_3['account']['internalId'] = '222'

    line_1['credit'] = 2 * line_1['credit']

    expected_lines = [line_1, line_2, line_3]

    assert constructed_lines == expected_lines


def test_construct_journal_entry_with_tax_balancing(create_journal_entry, add_tax_destination_attributes):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    configuration = Configuration.objects.get(workspace_id=1)
    general_mapping = GeneralMapping.objects.get(workspace_id=1)

    # without tax balancing
    journal_entry, journal_entry_lineitem = create_journal_entry
    journal_entry_lineitem[0].amount = 100
    journal_entry_lineitem[0].tax_amount = 3
    journal_entry_lineitem[0].tax_item_id = '103578'

    journal_entry_object = netsuite_connection._NetSuiteConnector__construct_journal_entry(journal_entry, journal_entry_lineitem, configuration, general_mapping)

    assert len(journal_entry_object['lineList']) == 2
    assert journal_entry_object['lineList'][1]['debit'] == 97
    assert journal_entry_object['lineList'][1]['taxCode']['internalId'] == '103578'
    assert journal_entry_object['lineList'][1]['grossAmt'] == 100
    assert journal_entry_object['lineList'][1]['tax1Amt'] == 3

    # with tax balancing
    general_mapping.is_tax_balancing_enabled = True
    general_mapping.save()

    journal_entry_object = netsuite_connection._NetSuiteConnector__construct_journal_entry(journal_entry, journal_entry_lineitem, configuration, general_mapping)

    assert len(journal_entry_object['lineList']) == 3
    assert journal_entry_object['lineList'][1]['debit'] == 60
    assert journal_entry_object['lineList'][1]['taxCode']['internalId'] == '103578'
    assert journal_entry_object['lineList'][2]['debit'] == 37
    assert journal_entry_object['lineList'][2]['taxCode']['internalId'] == general_mapping.default_tax_code_id
    assert journal_entry_object['lineList'][1]['grossAmt'] == 63
    assert journal_entry_object['lineList'][2]['grossAmt'] == 37
    assert journal_entry_object['lineList'][1]['tax1Amt'] == 3

    # with tax balancing enabled and right tax amount
    journal_entry_lineitem[0].amount = 100
    journal_entry_lineitem[0].tax_amount = 4.76
    journal_entry_lineitem[0].tax_item_id = '103578'

    journal_entry_object = netsuite_connection._NetSuiteConnector__construct_journal_entry(journal_entry, journal_entry_lineitem, configuration, general_mapping)

    assert len(journal_entry_object['lineList']) == 2
    assert journal_entry_object['lineList'][1]['debit'] == 95.24
    assert journal_entry_object['lineList'][1]['taxCode']['internalId'] == '103578'
    assert journal_entry_object['lineList'][1]['tax1Amt'] == 4.76
    assert journal_entry_object['lineList'][1]['grossAmt'] == 100

    general_mapping.is_tax_balancing_enabled = False
    general_mapping.save()


def test_contruct_credit_card_charge(create_credit_card_charge):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)
    general_mapping = GeneralMapping.objects.get(workspace_id=49)


    credit_card_charge, credit_card_charge_lineitems = create_credit_card_charge
    credit_card_charge_object = netsuite_connection._NetSuiteConnector__construct_credit_card_charge(credit_card_charge, credit_card_charge_lineitems, general_mapping, [])
    
    credit_card_charge_object['tranDate'] = data['credit_card_charge'][0]['tranDate']
    credit_card_charge_object['tranid'] = data['credit_card_charge'][0]['tranid']

    assert credit_card_charge_object == data['credit_card_charge'][0]


def test_contruct_credit_card_charge_with_tax_balancing(create_credit_card_charge, add_tax_destination_attributes):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)
    general_mapping = GeneralMapping.objects.get(workspace_id=49)

    # without tax balancing
    credit_card_charge, credit_card_charge_lineitems = create_credit_card_charge

    item = credit_card_charge_lineitems[0]
    item.amount = 100
    item.tax_amount = 3
    item.tax_item_id = '103578'

    credit_card_charge_object = netsuite_connection._NetSuiteConnector__construct_credit_card_charge(credit_card_charge, credit_card_charge_lineitems, general_mapping, [])
    
    assert len(credit_card_charge_object['expenses']) == 1
    assert credit_card_charge_object['expenses'][0]['amount'] == 97
    assert credit_card_charge_object['expenses'][0]['taxCode']['internalId'] == '103578'

    # with tax balancing
    general_mapping.is_tax_balancing_enabled = True
    general_mapping.save()

    credit_card_charge_object = netsuite_connection._NetSuiteConnector__construct_credit_card_charge(credit_card_charge, credit_card_charge_lineitems, general_mapping, [])

    assert len(credit_card_charge_object['expenses']) == 2
    assert credit_card_charge_object['expenses'][0]['amount'] == 60
    assert credit_card_charge_object['expenses'][0]['taxCode']['internalId'] == '103578'
    assert credit_card_charge_object['expenses'][1]['amount'] == 37
    assert credit_card_charge_object['expenses'][1]['taxCode']['internalId'] == general_mapping.default_tax_code_id

    # with tax balancing enabled and right tax amount
    item.amount = 100
    item.tax_amount = 4.76
    item.tax_item_id = '103578'

    credit_card_charge_object = netsuite_connection._NetSuiteConnector__construct_credit_card_charge(credit_card_charge, credit_card_charge_lineitems, general_mapping, [])

    assert len(credit_card_charge_object['expenses']) == 1
    assert credit_card_charge_object['expenses'][0]['amount'] == 95.24
    assert credit_card_charge_object['expenses'][0]['taxCode']['internalId'] == '103578'


def test_post_vendor(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.post',
        return_value=data['post_vendor']
    )
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    
    vendor = netsuite_connection.post_vendor(expense_group=expense_group, merchant='Nilesh')

    assert dict_compare_keys(vendor, data['post_vendor']) == [], 'post vendor api return diffs in keys'

    with mock.patch('netsuitesdk.api.vendors.Vendors.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError({
            'message': {'isperson': True}
        }), None]
        netsuite_connection.post_vendor(expense_group=expense_group, merchant='Nilesh')

    with mock.patch('netsuitesdk.api.vendors.Vendors.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError({
            'message': 'That record does not exist'
        }), None]
        netsuite_connection.post_vendor(expense_group=expense_group, merchant='Nilesh')
    

def test_get_bill(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendor_bills.VendorBills.get',
        return_value=data['get_bill_response'][0]
    )
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    bill = netsuite_connection.get_bill(238)
    
    assert dict_compare_keys(bill, data['get_bill_response'][0]) == [], 'get bill api return diffs in keys'


def test_get_expense_report(mocker, db):
    mocker.patch(
        'netsuitesdk.api.expense_reports.ExpenseReports.get',
        return_value=data['get_expense_report_response'][0]   
    )
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_report = netsuite_connection.get_expense_report(85327)
    assert dict_compare_keys(expense_report, data['get_expense_report_response'][0]) == [], 'get expense report returns diff in keys'

def test_sync_vendors(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.count',
        return_value=0
    )
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.get_records_generator',
        return_value=data['get_all_vendors']   
    )
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
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

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert project_count == 1086

    netsuite_connection.sync_projects()

    new_project_count = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert new_project_count == 1087

def test_sync_employees(mocker, db):
    mocker.patch(
        'netsuitesdk.api.employees.Employees.count',
        return_value=6
    )
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=data['get_all_employees']    
    )
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get',
        return_value=data['get_all_employees'][0][0]
    )

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
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
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    accounts_count = DestinationAttribute.objects.filter(attribute_type='ACCOUNT', workspace_id=1).count()
    assert accounts_count == 123

    netsuite_connection.sync_accounts()

    new_account_counts = DestinationAttribute.objects.filter(attribute_type='ACCOUNT', workspace_id=1).count()
    assert new_account_counts == 124

@pytest.mark.django_db()
def test_sync_items(mocker, db):
    mocker.patch('netsuitesdk.api.items.Items.count', return_value=3)
    
    with mock.patch('netsuitesdk.api.items.Items.get_all_generator') as mock_call:
        # here we have the import_items set to false , So none of the destination attributes should be active
        configuration = Configuration.objects.get(workspace_id=1)
        configuration.import_items = False
        configuration.save()

        mock_call.return_value = data['get_all_items']

        netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
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

        netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
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
        'netsuitesdk.api.expense_categories.ExpenseCategory.count',
        return_value=1
    )
    mocker.patch(
        'netsuitesdk.api.expense_categories.ExpenseCategory.get_all_generator',
        return_value=data['get_all_expense_categories']
    )
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
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
    
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=49)
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
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=49)
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
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=49)
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
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    departments = DestinationAttribute.objects.filter(attribute_type='DEPARTMENT', workspace_id=49).count()
    assert departments == 12

    netsuite_connection.sync_departments()

    departments = DestinationAttribute.objects.filter(attribute_type='DEPARTMENT', workspace_id=49).count()
    assert departments == 13


def test_sync_customers(mocker, db):
    mocker.patch(
        'netsuitesdk.api.customers.Customers.get_records_generator',
        return_value=data['get_all_projects']  
    )

    mocker.patch(
        'netsuitesdk.api.customers.Customers.count',
        return_value=len(data['get_all_projects'][0])
    )

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    customers = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert customers == 1086

    netsuite_connection.sync_customers()

    customers = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    assert customers == 1087


def test_sync_tax_items(mocker, db):
    mocker.patch(
        'netsuitesdk.api.tax_items.TaxItems.count',
        return_value=6
    )
    mocker.patch(
        'netsuitesdk.api.tax_items.TaxItems.get_all_generator',
        return_value=data['get_all_tax_items']    
    )

    mocker.patch(
        'netsuitesdk.api.tax_groups.TaxGroups.get_all_generator',
        return_value=data['get_all_tax_groups']
    )

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    tax_items = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='TAX_ITEM').count()
    assert tax_items == 26

    netsuite_connection.sync_tax_items()

    tax_items = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='TAX_ITEM').count()
    assert tax_items == 32


def test_sync_currencies(mocker, db):
    mocker.patch(
        'netsuitesdk.api.currencies.Currencies.count',
        return_value=1
    )
    mocker.patch(
        'netsuitesdk.api.currencies.Currencies.get_all_generator',
        return_value=data['get_all_currencies'][0]
    )
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=49)
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
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=49)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=49)

    classifications = DestinationAttribute.objects.filter(attribute_type='CLASS', workspace_id=49).count()
    assert classifications == 18

    # Test without import_classes_with_parent (default behavior)
    netsuite_connection.sync_classifications()

    classifications = DestinationAttribute.objects.filter(attribute_type='CLASS', workspace_id=49).count()
    assert classifications == 19

    # Verify that classifications without parents keep their original names
    hardware_classification = DestinationAttribute.objects.filter(
        attribute_type='CLASS', 
        workspace_id=49, 
        destination_id='992djj'
    ).first()
    assert hardware_classification.value == 'Hardware Fartware'

    # Verify that classifications with parents also keep their original names (no parent prefix)
    office_classification = DestinationAttribute.objects.filter(
        attribute_type='CLASS', 
        workspace_id=49, 
        destination_id='3'
    ).first()
    assert office_classification.value == 'Office'

    # Test with import_classes_with_parent enabled
    configuration = Configuration.objects.get(workspace_id=49)
    configuration.import_classes_with_parent = True
    configuration.save()

    # Clear existing classifications to test fresh import
    DestinationAttribute.objects.filter(attribute_type='CLASS', workspace_id=49).delete()

    netsuite_connection.sync_classifications()

    classifications = DestinationAttribute.objects.filter(attribute_type='CLASS', workspace_id=49).count()
    assert classifications == 5  # Total classifications from test data

    # Verify that classifications without parents keep their original names
    hardware_classification = DestinationAttribute.objects.filter(
        attribute_type='CLASS', 
        workspace_id=49, 
        destination_id='992djj'
    ).first()
    assert hardware_classification.value == 'Hardware Fartware'

    # Verify that classifications with parents get formatted with parent name
    office_classification = DestinationAttribute.objects.filter(
        attribute_type='CLASS', 
        workspace_id=49, 
        destination_id='3'
    ).first()
    assert office_classification.value == 'Furniture : Office'

    # Reset configuration for other tests
    configuration.import_classes_with_parent = False
    configuration.save()


def test_get_or_create_vendor(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value=data['search_vendor']
    )
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
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
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
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
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()

    employee_attribute = ExpenseAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1).first()
    
    vendor = netsuite_connection.post_employee(expense_group=expense_group, employee=employee_attribute)

    assert dict_compare_keys(vendor, data['post_vendor']) == [], 'post vendor api return diffs in keys'


def test_post_credit_card_charge_exception(db, mocker, create_credit_card_charge):
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=workspace_id)
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

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=workspace_id)
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

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)
    general_mapping = GeneralMapping.objects.get(workspace_id=workspace_id)
    feature_config = FeatureConfig.objects.get(workspace_id=workspace_id)

    bill_transaction, bill_transaction_lineitems = create_bill_account_based

    workspace_general_setting = Configuration.objects.get(workspace_id=workspace_id)
    workspace_general_setting.change_accounting_period = True
    workspace_general_setting.save()

    with mock.patch('netsuitesdk.api.vendor_bills.VendorBills.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError('An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'), None]
        netsuite_connection.post_bill(bill_transaction, bill_transaction_lineitems, general_mapping)


def test_post_expense_report_exception(db, mocker, create_expense_report):
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)
    general_mapping = GeneralMapping.objects.get(workspace_id=workspace_id)

    expense_report_transaction, expense_report_transaction_lineitems = create_expense_report

    workspace_general_setting = Configuration.objects.get(workspace_id=workspace_id)
    workspace_general_setting.change_accounting_period = True
    workspace_general_setting.save()
    feature_config = FeatureConfig.objects.get(workspace_id=workspace_id)

    with mock.patch('netsuitesdk.api.expense_reports.ExpenseReports.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError('An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'), None]
        netsuite_connection.post_expense_report(expense_report_transaction, expense_report_transaction_lineitems, general_mapping)


def test_post_journal_entry_exception(db, mocker, create_journal_entry):
    workspace_id = 1

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)
    general_mapping = GeneralMapping.objects.get(workspace_id=workspace_id)

    journal_entry_transaction, journal_entry_transaction_lineitems = create_journal_entry

    configuration = Configuration.objects.get(workspace_id=workspace_id)

    workspace_general_setting = Configuration.objects.get(workspace_id=workspace_id)
    workspace_general_setting.change_accounting_period = True
    workspace_general_setting.save()

    with mock.patch('netsuitesdk.api.journal_entries.JournalEntries.post') as mock_call:
        mock_call.side_effect = [NetSuiteRequestError('An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'), None]
        netsuite_connection.post_journal_entry(journal_entry_transaction, journal_entry_transaction_lineitems, configuration, general_mapping)

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

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=workspace_id)
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


def test_update_destination_attributes_with_duplicate_values(db, mocker):
    """
    Test the scenario mentioned in the comments:
    - value 'Duplicate Type' with destination_id '1' -> in db
    - they update 'Duplicate Type' with destination_id '2' in the api response
    - another update 'Duplicate Type' with destination_id '3' in the api response
    - we want to save the last updated destination_id ('3') in the db
    """
    mocker.patch(
        'netsuitesdk.api.custom_record_types.CustomRecordTypes.get_all_by_id',
        return_value=data['custom_records_with_duplicates']
    )

    workspace = Workspace.objects.get(id=1)
    DestinationAttribute.objects.create(
        attribute_type='CUSTOM_TYPE',
        display_name='custom_type',
        value='Duplicate Type',
        destination_id='1',
        auto_created=False,
        active=True,
        detail={},
        workspace=workspace
    )

    workspace_id = 1
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    custom_records = netsuite_connection.connection.custom_record_types.get_all_by_id('1')
    netsuite_connection.update_destination_attributes('CUSTOM_TYPE', custom_records)

    duplicate_type_attributes = DestinationAttribute.objects.filter(
        attribute_type='CUSTOM_TYPE',
        workspace_id=1,
        value='Duplicate Type'
    )

    assert duplicate_type_attributes.count() == 1

    duplicate_type_attribute = duplicate_type_attributes.first()
    assert duplicate_type_attribute.destination_id == '3'


def test_skip_sync_attributes(mocker, db):
    mocker.patch(
        'netsuitesdk.api.projects.Projects.count',
        return_value=35000
    )

    mocker.patch(
        'netsuitesdk.api.classifications.Classifications.count',
        return_value=35000
    )
    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.count',
        return_value=35000
    )
    mocker.patch(
        'netsuitesdk.api.locations.Locations.count',
        return_value=35000
    )
    mocker.patch(
        'netsuitesdk.api.departments.Departments.count',
        return_value=35000
    )
    mocker.patch(
        'netsuitesdk.api.customers.Customers.count',
        return_value=35000
    )
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.count',
        return_value=35000
    )

    today = timezone.now()
    Workspace.objects.filter(id=1).update(created_at=today)
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
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

def test_all_sync_methods_skip_when_over_limit(mocker, db):
    mocker.patch('netsuitesdk.api.accounts.Accounts.count', return_value=35000)
    mocker.patch('netsuitesdk.api.expense_categories.ExpenseCategory.count', return_value=35000)
    mocker.patch('netsuitesdk.api.items.Items.count', return_value=35000)
    mocker.patch('netsuitesdk.api.locations.Locations.count', return_value=35000)
    mocker.patch('netsuitesdk.api.classifications.Classifications.count', return_value=35000)
    mocker.patch('netsuitesdk.api.departments.Departments.count', return_value=35000)
    mocker.patch('netsuitesdk.api.vendors.Vendors.count', return_value=35000)
    mocker.patch('netsuitesdk.api.employees.Employees.count', return_value=35000)
    mocker.patch('netsuitesdk.api.tax_items.TaxItems.count', return_value=35000)
    mocker.patch('netsuitesdk.api.projects.Projects.count', return_value=35000)
    mocker.patch('netsuitesdk.api.customers.Customers.count', return_value=35000)
    workspace = Workspace.objects.get(id=1)
    workspace.created_at = timezone.now()
    workspace.save()
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    accounts_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='ACCOUNT').count()
    netsuite_connection.sync_accounts()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='ACCOUNT').count() == accounts_count_before
    expense_categories_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='EXPENSE_CATEGORY').count()
    netsuite_connection.sync_expense_categories()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='EXPENSE_CATEGORY').count() == expense_categories_count_before
    items_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='ACCOUNT', display_name='Item').count()
    netsuite_connection.sync_items()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='ACCOUNT', display_name='Item').count() == items_count_before
    locations_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='LOCATION').count()
    netsuite_connection.sync_locations()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='LOCATION').count() == locations_count_before
    classifications_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='CLASS').count()
    netsuite_connection.sync_classifications()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='CLASS').count() == classifications_count_before
    departments_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='DEPARTMENT').count()
    netsuite_connection.sync_departments()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='DEPARTMENT').count() == departments_count_before
    vendors_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='VENDOR').count()
    netsuite_connection.sync_vendors()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='VENDOR').count() == vendors_count_before
    employees_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='EMPLOYEE').count()
    netsuite_connection.sync_employees()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='EMPLOYEE').count() == employees_count_before
    tax_items_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='TAX_ITEM').count()
    netsuite_connection.sync_tax_items()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='TAX_ITEM').count() == tax_items_count_before
    projects_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    netsuite_connection.sync_projects()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count() == projects_count_before
    customers_count_before = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='CUSTOMER').count()
    netsuite_connection.sync_customers()
    assert DestinationAttribute.objects.filter(workspace_id=1, attribute_type='CUSTOMER').count() == customers_count_before


def test_constructs_tax_details_list_for_multiple_items(mocker, db):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)

    # Create a more complete mock Mapping object
    mock_mapping = mocker.Mock()
    mock_mapping.destination.destination_id = 'tax_code_1'
    mock_mapping.destination.detail.get.return_value = 'tax_type_1'
    mock_mapping.destination.detail.all.return_value = [mocker.Mock(value=10.0)]

    # Mock get_tax_group_mapping to return our complete mock mapping
    mocker.patch(
        'apps.netsuite.models.get_tax_group_mapping',
        return_value=mock_mapping
    )

    # Creating mock expense objects with workspace_id and tax_group_id
    expense1 = mocker.Mock(
        amount=100.0,
        tax_amount=10.0,
        expense_number='EXP001',
        workspace_id=1,
        tax_group_id=1
    )
    
    expense2 = mocker.Mock(
        amount=200.0,
        tax_amount=20.0,
        expense_number='EXP002',
        workspace_id=1,
        tax_group_id=1
    )

    # Creating mock bill line items with expense attribute and workspace_id
    bill_lineitem1 = mocker.Mock(
        expense=expense1,
        workspace_id=1
    )
    bill_lineitem2 = mocker.Mock(
        expense=expense2,
        workspace_id=1
    )

    bill_lineitems = [bill_lineitem1, bill_lineitem2]

    result = netsuite_connection.construct_tax_details_list(bill_lineitems)

    assert result == data['tax_list_detail']


def test_is_sync_allowed(db):
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    assert netsuite_connection.is_sync_allowed(attribute_count=1000) is True
    assert netsuite_connection.is_sync_allowed(attribute_count=30000) is True
    workspace = Workspace.objects.get(id=1)
    old_date = timezone.make_aware(datetime(2024, 9, 1), timezone.get_current_timezone())
    workspace.created_at = old_date
    workspace.save()
    assert netsuite_connection.is_sync_allowed(attribute_count=35000) is True
    new_date = timezone.make_aware(datetime(2024, 11, 1), timezone.get_current_timezone())
    workspace.created_at = new_date
    workspace.save()
    assert netsuite_connection.is_sync_allowed(attribute_count=35000) is False
