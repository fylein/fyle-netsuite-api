from datetime import datetime
import pytest
import json
from apps.fyle.models import Expense, ExpenseGroup
from apps.netsuite.models import BillLineitem, ExpenseReport, ExpenseReportLineItem, get_department_id_or_none, get_transaction_date, get_expense_purpose, \
    get_location_id_or_none, get_customer_id_or_none, Bill

@pytest.mark.django_db(databases=['default'])
def test_get_department_id_or_none(test_connection):

    expense = Expense.objects.get(id=1)
    expense_group = ExpenseGroup.objects.get(id=1)

    department_id = get_department_id_or_none(expense_group, expense)
    
    assert department_id == None


@pytest.mark.django_db(databases=['default'])
@pytest.mark.parametrize(
    "test_input, expected",
    [(1, datetime.now().strftime('%Y-%m-%dT%H:%M:%S')), (4, '2021-11-16')],
)
def test_get_transaction_date(test_input, expected):
    expense_group = ExpenseGroup.objects.get(id=test_input)

    transaction_date =  get_transaction_date(expense_group)
    assert transaction_date >= expected


@pytest.mark.django_db(databases=['default'])
def test_get_expense_purpose():
    expense_group = ExpenseGroup.objects.get(id=1)
    expenses = expense_group.expenses.all()
    
    for lineitem in expenses:
        category = lineitem.category if lineitem.category == lineitem.sub_category else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)
        
        expense_purpose = get_expense_purpose(lineitem, category)
        
        assert expense_purpose == 'Expense by ashwin.t@fyle.in against category Accounts Payable spent on 2021-11-15 with report number - C/2021/11/R/5'


@pytest.mark.django_db(databases=['default'])
def test_get_location_id_or_none():
    expense_group = ExpenseGroup.objects.get(id=4)
    expenses = expense_group.expenses.all()

    for lineitem in expenses:
        location_id = get_location_id_or_none(expense_group, lineitem)
        assert location_id == None


@pytest.mark.django_db(databases=['default'])
def test_get_customer_id_or_none():
    expense_group = ExpenseGroup.objects.get(id=4)
    expenses = expense_group.expenses.all()

    for lineitem in expenses:
        customer_id = get_customer_id_or_none(expense_group, lineitem)
        assert customer_id==None


def test_create_bill(db):

    expense_group = ExpenseGroup.objects.get(id=2)
    bill = Bill.create_bill(expense_group)
    bill_lineitems = BillLineitem.create_bill_lineitems(expense_group)

    for bill_lineitem in bill_lineitems:
        assert bill_lineitem.amount == 100.00
        assert bill_lineitem.memo == 'Expense by ashwin.t@fyle.in against category Accounts Payable spent on 2021-11-15 with report number - C/2021/11/R/6'
        assert bill_lineitem.billable == None

    assert bill.currency == '1'
    assert bill.transaction_date == datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    assert bill.subsidiary_id == '3'

def test_create_expense_report(db):

    expense_group = ExpenseGroup.objects.get(id=1)
    expense_report = ExpenseReport.create_expense_report(expense_group)

    expense_report_lineitems = ExpenseReportLineItem.create_expense_report_lineitems(expense_group)

    for expense_report_lineitem in expense_report_lineitems:
        assert expense_report_lineitem.category == '13'
        assert expense_report_lineitem.amount == 50.0
        assert expense_report_lineitem.currency == '1'
        assert expense_report_lineitem.memo == 'Expense by ashwin.t@fyle.in against category Accounts Payable spent on 2021-11-15 with report number - C/2021/11/R/5'
        assert expense_report_lineitem.transaction_date >= '2021-11-29T13:51:20'

    assert expense_report.currency == '1'
    assert expense_report.account_id == '118'
    assert expense_report.location_id == '8'
    


