import pytest
from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog
from apps.netsuite.models import Bill, BillLineitem, CreditCardCharge, CreditCardChargeLineItem, ExpenseReport, ExpenseReportLineItem, JournalEntry, JournalEntryLineItem
from apps.workspaces.models import Configuration
from apps.netsuite.models import CustomSegment
from apps.fyle.models import ExpenseGroup, Expense
from fyle_accounting_mappings.models import  ExpenseAttribute, DestinationAttribute, CategoryMapping
from datetime import datetime
import json


def create_item_based_mapping(workspace_id):
    destination_attribute = DestinationAttribute.objects.create(
        attribute_type='ACCOUNT',
        display_name='Item',
        value='Concrete',
        destination_id=3,
        workspace_id=workspace_id,
        active=True
    )
    expense_attribute = ExpenseAttribute.objects.create(
        attribute_type='CATEGORY',
        display_name='Category',
        value='Concrete',
        source_id='253737253737',
        workspace_id=workspace_id,
        active=True
    )
    CategoryMapping.objects.create(
        destination_account_id = destination_attribute.id,
        source_category_id = expense_attribute.id,
        workspace_id=workspace_id
    )

@pytest.fixture(autouse=True)
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
    # Clear existing TaskLogs for this expense group
    TaskLog.objects.filter(expense_group_id=1).delete()
    
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
    configuration = Configuration.objects.get(workspace_id=1)
    expense_report = ExpenseReport.create_expense_report(expense_group)
    expense_report_lineitems = ExpenseReportLineItem.create_expense_report_lineitems(expense_group, configuration)

    return expense_report, expense_report_lineitems


@pytest.fixture
def create_bill_account_based(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.get(id=2)
    configuration = Configuration.objects.get(workspace_id=1)
    bill = Bill.create_bill(expense_group)
    bill_lineitem  = BillLineitem.create_bill_lineitems(expense_group, configuration)

    return bill, bill_lineitem


@pytest.fixture
def create_bill_item_based(db, add_netsuite_credentials, add_fyle_credentials):
    expense = Expense.objects.create(
        employee_email='sravan.kumar@fyle.in',
        employee_name='sravan k',
        category= 'Concrete',
        expense_id='txT4kpMbHdKn1',
        project= 'Bebe Rexha',
        expense_number= 'E/2023/04/T/11',
        org_id= 'orPJvXuoLqvJ',
        claim_number= 'C/2023/04/R/11',
        amount= 1,
        currency= 'USD',
        settlement_id= 'setuFjoPoH1FN1',
        reimbursable= False,
        billable= False,
        state= 'PAYMENT_PROCESSING',
        vendor= None,
        cost_center= 'Adidas',
        report_id= 'rpcegBZcwUkH1',
        spent_at= datetime.now(),
        approved_at= datetime.now(),
        expense_created_at= datetime.now(),
        expense_updated_at= datetime.now(),
        custom_properties=json.loads('{"Card": "", "Killua": "", "Classes": "", "avc_123": null, "New Field": "", "Multi field": "", "Testing This": "", "abc in [123]": null, "POSTMAN FIELD": "", "Netsuite Class": ""}'),
        fund_source= 'CCC'
    )


    expense_group = ExpenseGroup.objects.create(
        workspace_id=1,
        fund_source='CCC',
        description=json.loads('{"report_id": "rpcegBZcwUkH", "fund_source": "CCC", "claim_number": "C/2023/04/R/1", "employee_email": "sravan.kumar@fyle.in"}'),   
    )

    expense_group.expenses.add(expense)
    
    create_item_based_mapping(workspace_id=1)

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.import_items = True
    expense_group = ExpenseGroup.objects.get(id=expense_group.id)
    bill = Bill.create_bill(expense_group)
    bill_lineitem = BillLineitem.create_bill_lineitems(expense_group, configuration)

    return bill, bill_lineitem

@pytest.fixture
def create_bill_item_and_account_based(db, add_netsuite_credentials, add_fyle_credentials):
    expense_1 = Expense.objects.create(
        employee_email='sravan.kumar@fyle.in',
        employee_name='sravan k',
        category= 'Concrete',
        expense_id='txT4kpMbHdKn1',
        project= 'Bebe Rexha',
        expense_number= 'E/2023/04/T/11',
        org_id= 'orPJvXuoLqvJ',
        claim_number= 'C/2023/04/R/11',
        amount= 1,
        currency= 'USD',
        settlement_id= 'setuFjoPoH1FN1',
        reimbursable= False,
        billable= False,
        state= 'PAYMENT_PROCESSING',
        vendor= None,
        cost_center= 'Adidas',
        report_id= 'rpcegBZcwUkH1',
        spent_at= datetime.now(),
        approved_at= datetime.now(),
        expense_created_at= datetime.now(),
        expense_updated_at= datetime.now(),
        custom_properties=json.loads('{"Card": "", "Killua": "", "Classes": "", "avc_123": null, "New Field": "", "Multi field": "", "Testing This": "", "abc in [123]": null, "POSTMAN FIELD": "", "Netsuite Class": ""}'),
        fund_source= 'CCC'
    )

    expense_2 = Expense.objects.create(
        employee_email='sravan.kumar@fyle.in',
        employee_name='sravan k',
        category= 'Accounts Payable',
        expense_id='txT4kpMbHdKn12',
        project= 'Bebe Rexha',
        expense_number= 'E/2023/04/T/12',
        org_id= 'orPJvXuoLqvJ',
        claim_number= 'C/2023/04/R/12',
        amount= 1,
        currency= 'USD',
        settlement_id= 'setuFjoPoH1FN1',
        reimbursable= False,
        billable= False,
        state= 'PAYMENT_PROCESSING',
        vendor= None,
        cost_center= 'Adidas',
        report_id= 'rpcegBZcwUkH12',
        spent_at= datetime.now(),
        approved_at= datetime.now(),
        expense_created_at= datetime.now(),
        expense_updated_at= datetime.now(),
        custom_properties=json.loads('{"Card": "", "Killua": "", "Classes": "", "avc_123": null, "New Field": "", "Multi field": "", "Testing This": "", "abc in [123]": null, "POSTMAN FIELD": "", "Netsuite Class": ""}'),
        fund_source= 'CCC'
    )


    expense_group = ExpenseGroup.objects.create(
        workspace_id=1,
        fund_source='CCC',
        description=json.loads('{"report_id": "rpcegBZcwUkH", "fund_source": "CCC", "claim_number": "C/2023/04/R/1", "employee_email": "sravan.kumar@fyle.in"}'),   
    )

    expense_group.expenses.add(*[expense_1, expense_2])
    
    create_item_based_mapping(workspace_id=1)

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.import_items = True
    expense_group = ExpenseGroup.objects.get(id=expense_group.id)
    bill = Bill.create_bill(expense_group)
    bill_lineitem = BillLineitem.create_bill_lineitems(expense_group, configuration)

    return bill, bill_lineitem

@pytest.fixture
def create_bill_task(db, add_netsuite_credentials, add_fyle_credentials):

    TaskLog.objects.update_or_create(
        workspace_id=1,
        expense_group_id=1,
        type='FETCHING_EXPENSES',
        detail={
          'internalId': 389508
        },
        defaults={
            'status': 'COMPLETE'
        }
    )

    expense_group = ExpenseGroup.objects.get(id=1)
    configuration = Configuration.objects.get(workspace_id=1)
    bill = Bill.create_bill(expense_group)
    bill_lineitem  = BillLineitem.create_bill_lineitems(expense_group, configuration)

    return bill, bill_lineitem


@pytest.fixture
def create_journal_entry(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).first()
    configuration = Configuration.objects.get(workspace_id=1)
    journal_entry = JournalEntry.create_journal_entry(expense_group)
    journal_entry_lineitem = JournalEntryLineItem.create_journal_entry_lineitems(expense_group, configuration)

    return journal_entry, journal_entry_lineitem


@pytest.fixture
def create_credit_card_charge(db, add_netsuite_credentials, add_fyle_credentials):

    expense_group = ExpenseGroup.objects.filter(workspace_id=49).last()
    configuration = Configuration.objects.get(workspace_id=1)
    credit_card_charge_object = CreditCardCharge.create_credit_card_charge(expense_group)

    credit_card_charge_lineitems_object = CreditCardChargeLineItem.create_credit_card_charge_lineitem(
        expense_group, configuration
    )

    return credit_card_charge_object, credit_card_charge_lineitems_object


@pytest.fixture(autouse=True)
def add_custom_segment(db):
    custom_segments = [{
        'name': 'KLASS',
        'segment_type': 'CUSTOM_RECORD',
        'script_id': 'custcol780',
        'internal_id': '476',
        'workspace_id': 2  
    },
    {
        'name': 'FAVOURITE_SINGER',
        'segment_type': 'CUSTOM_LIST',
        'script_id': 'custcol780',
        'internal_id': '491',
        'workspace_id': 49  
    }, 
    {
        'name': 'PRODUCTION_LINE',
        'segment_type': 'CUSTOM_SEGMENT',
        'script_id': 'custcolauto',
        'internal_id': '1',
        'workspace_id': 49  
    }]

    for i in range(0, len(custom_segments)):
        custom_segments[i] = CustomSegment(**custom_segments[i])

    CustomSegment.objects.bulk_create(custom_segments)
