from datetime import datetime
import pytest
from apps.netsuite.connector import NetSuiteConnector, NetSuiteCredentials
from apps.netsuite.tasks import create_journal_entry
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
