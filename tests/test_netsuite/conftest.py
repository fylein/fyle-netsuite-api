import pytest
from apps.fyle.models import Expense, ExpenseGroup
from apps.tasks.models import TaskLog
from apps.netsuite.models import Bill, BillLineitem, CreditCardCharge, CreditCardChargeLineItem, ExpenseReport, ExpenseReportLineItem, JournalEntry, JournalEntryLineItem

@pytest.fixture
def create_task_logs(db):
    TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

    TaskLog.objects.update_or_create(
        workspace_id=2,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

    TaskLog.objects.update_or_create(
        workspace_id=49,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

@pytest.fixture
def create_expense_report(db, add_netsuite_credentials, add_fyle_credentials):

    TaskLog.objects.update_or_create(
        workspace_id=2,
        expense_group_id=1,
        type='FETCHING_EXPENSES',
        detail={
          'internalId': 10913
        },
        defaults={
            'status': 'COMPLETE'
        }
    )

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expense_report = ExpenseReport.create_expense_report(expense_group)
    expense_report_lineitems = ExpenseReportLineItem.create_expense_report_lineitems(expense_group)

    return expense_report, expense_report_lineitems

@pytest.fixture
def create_bill(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.get(id=2)
    bill = Bill.create_bill(expense_group)
    bill_lineitem  = BillLineitem.create_bill_lineitems(expense_group)

    return bill, bill_lineitem

@pytest.fixture
def create_journal_entry(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).first()
    journal_entry = JournalEntry.create_journal_entry(expense_group)
    journal_entry_lineitem = JournalEntryLineItem.create_journal_entry_lineitems(expense_group)

    return journal_entry, journal_entry_lineitem


@pytest.fixture
def create_credit_card_charge(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).last()
    credit_card_charge_object = CreditCardCharge.create_credit_card_charge(expense_group)

    credit_card_charge_lineitems_object = CreditCardChargeLineItem.create_credit_card_charge_lineitem(
        expense_group
    )

    return credit_card_charge_object, credit_card_charge_lineitems_object

