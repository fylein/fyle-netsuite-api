from datetime import datetime
import pytest

from apps.fyle.models import Expense, ExpenseGroup
from apps.netsuite.models import BillLineitem, ExpenseReport, ExpenseReportLineItem, get_department_id_or_none, get_transaction_date, get_expense_purpose, \
    get_location_id_or_none, get_customer_id_or_none, Bill, get_class_id_or_none, get_location_id_or_none, get_custom_segments, CreditCardChargeLineItem, CreditCardCharge 
from apps.workspaces.models import Configuration
from fyle_accounting_mappings.models import Mapping, MappingSetting
from apps.mappings.models import GeneralMapping

@pytest.mark.django_db(databases=['default'])
def test_get_department_id_or_none(test_connection):

    expense = Expense.objects.get(id=1)
    expense_group = ExpenseGroup.objects.get(id=1)
    expense_group.workspace_id = 1
    expense_group.save()

    department_id = get_department_id_or_none(expense_group, expense)
    
    assert department_id == None

    mapping_setting = MappingSetting.objects.filter(
        workspace_id=1).first()
    mapping_setting.destination_field = 'DEPARTMENT'
    mapping_setting.save()

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
        category = lineitem.category if (lineitem.category == lineitem.sub_category or lineitem.sub_category == None) else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

        configuration = Configuration.objects.get(workspace_id=1)
        expense_purpose = get_expense_purpose(lineitem, category, configuration)
        
        assert expense_purpose == 'ashwin.t@fyle.in - Accounts Payable - 2021-11-15 - C/2021/11/R/5 - '


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
    configuration = Configuration.objects.get(workspace_id=1)
    bill_lineitems = BillLineitem.create_bill_lineitems(expense_group, configuration)

    for bill_lineitem in bill_lineitems:
        assert bill_lineitem.amount == 100.00
        assert bill_lineitem.memo == 'ashwin.t@fyle.in - Accounts Payable - 2021-11-15 - C/2021/11/R/6 - '
        assert bill_lineitem.billable == None

    assert bill.currency == '1'
    assert bill.transaction_date <= datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    assert bill.subsidiary_id == '3'

    expense_group = ExpenseGroup.objects.get(id=2)

    general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id) 
    general_mappings.use_employee_class = True
    general_mappings.use_employee_department = True
    general_mappings.department_level = 'ALL'
    general_mappings.use_employee_location = True
    general_mappings.location_level = 'ALL'
    general_mappings.save()

    bill = Bill.create_bill(expense_group)
    configuration = Configuration.objects.get(workspace_id=1)
    bill_lineitems = BillLineitem.create_bill_lineitems(expense_group, configuration)

    for bill_lineitem in bill_lineitems:
        assert bill_lineitem.amount == 100.00
        assert bill_lineitem.memo == 'ashwin.t@fyle.in - Accounts Payable - 2021-11-15 - C/2021/11/R/6 - '
        assert bill_lineitem.billable == None

    print(bill.__dict__)
    assert bill.currency == '1'
    assert bill.transaction_date <= datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    assert bill.subsidiary_id == '3'


def test_create_expense_report(db):

    expense_group = ExpenseGroup.objects.get(id=1)
    expense_report = ExpenseReport.create_expense_report(expense_group)

    configuration = Configuration.objects.get(workspace_id=1)
    expense_report_lineitems = ExpenseReportLineItem.create_expense_report_lineitems(expense_group, configuration)

    for expense_report_lineitem in expense_report_lineitems:
        assert expense_report_lineitem.category == '13'
        assert expense_report_lineitem.amount == 50.0
        assert expense_report_lineitem.currency == '1'
        assert expense_report_lineitem.memo == 'ashwin.t@fyle.in - Accounts Payable - 2021-11-15 - C/2021/11/R/5 - '
        assert expense_report_lineitem.transaction_date >= '2021-11-29T13:51:20'

    assert expense_report.currency == '1'
    assert expense_report.account_id == '118'
    assert expense_report.location_id == '8'
    

def test_get_class_id_or_none(db, add_fyle_credentials):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    mapping_setting = MappingSetting.objects.filter(
        workspace_id=1).first()
    mapping_setting.destination_field = 'CLASS'
    mapping_setting.save()
    
    class_id = get_class_id_or_none(expense_group, expenses[0])
    assert class_id == None

    mapping_setting.source_field = 'COST_CENTER'
    mapping_setting.save()
    
    class_id = get_class_id_or_none(expense_group, expenses[0])
    assert class_id == None


def test_get_location_id_or_none(db, add_fyle_credentials):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    mapping_setting = MappingSetting.objects.filter(
        workspace_id=1).first()
    mapping_setting.destination_field = 'LOCATION'
    mapping_setting.save()
    
    location_id = get_location_id_or_none(expense_group, expenses[0])
    assert location_id == None

    mapping_setting.source_field = 'COST_CENTER'
    mapping_setting.save()
    
    location_id = get_location_id_or_none(expense_group, expenses[0])
    assert location_id == None


def test_get_custom_segments(db):
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expenses = expense_group.expenses.all()

    mapping_settings = MappingSetting.objects.filter(
        workspace_id=1)
    for mapping_setting in mapping_settings:
        mapping_setting.destination_field = 'CUSTOM'
        mapping_setting.save()

    get_custom_segments(expense_group, expenses[0])

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).first()
    expenses = expense_group.expenses.all()

    get_custom_segments(expense_group, expenses[0])



def test_create_credit_card_charge(db):

    expense_group = ExpenseGroup.objects.get(id=4)
    credit_card = CreditCardCharge.create_credit_card_charge(expense_group)
    configuration = Configuration.objects.get(workspace_id=2)
    credit_card_charge_lineitem = CreditCardChargeLineItem.create_credit_card_charge_lineitem(expense_group, configuration)

    assert credit_card_charge_lineitem.amount == 100.00
    assert credit_card_charge_lineitem.memo == 'ashwin.t@fyle.in - Accounts Payable - 2021-11-16 - C/2021/11/R/1 - '
    assert credit_card_charge_lineitem.billable == False

    assert credit_card.currency == '1'
    assert credit_card.transaction_date <= datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    assert credit_card.subsidiary_id == '5'

    expense_group = ExpenseGroup.objects.get(id=4)

    general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id) 
    general_mappings.use_employee_class = True
    general_mappings.use_employee_department = True
    general_mappings.department_level = 'ALL'
    general_mappings.use_employee_location = True
    general_mappings.location_level = 'ALL'
    general_mappings.save()

    credit_card = CreditCardCharge.create_credit_card_charge(expense_group)
    configuration = Configuration.objects.get(workspace_id=2)
    credit_card_charge_lineitem = CreditCardChargeLineItem.create_credit_card_charge_lineitem(expense_group, configuration)

    assert credit_card_charge_lineitem.amount == 100.00
    assert credit_card_charge_lineitem.memo == 'ashwin.t@fyle.in - Accounts Payable - 2021-11-16 - C/2021/11/R/1 - '
    assert credit_card_charge_lineitem.billable == False

    print(credit_card.__dict__)
    assert credit_card.currency == '1'
    assert credit_card.transaction_date <= datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    assert credit_card.subsidiary_id == '5'