from datetime import datetime
import pytest

from apps.fyle.models import Expense, ExpenseGroup
from apps.netsuite.models import *
from apps.netsuite.tasks import *
from apps.netsuite.queue import *
from apps.workspaces.models import Configuration
from fyle_accounting_mappings.models import Mapping, MappingSetting, DestinationAttribute, ExpenseAttribute
from apps.fyle.models import Expense, ExpenseGroup, Reimbursement, get_default_expense_group_fields, get_default_expense_state, \
    ExpenseGroupSettings, _group_expenses, get_default_ccc_expense_state
from apps.workspaces.models import Configuration, Workspace
from apps.tasks.models import TaskLog
from apps.fyle.tasks import create_expense_groups
from apps.mappings.models import GeneralMapping
from tests.test_fyle.fixtures import data as fyle_expense_data
from .fixtures import data

@pytest.mark.django_db(databases=['default'])
def test_get_department_id_or_none(access_token, mocker):
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.get_by_id',
        return_value={'options': ['samp'], 'updated_at': '2020-06-11T13:14:55.201598+00:00', 'is_mandatory': True}
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.post',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.sync',
        return_value=None
    )
    expense = Expense.objects.get(id=2)
    expense_group = ExpenseGroup.objects.get(id=2)
    expense_group.description.update({'klass': 'Klass'})
    expense_group.workspace_id = 2
    expense_group.save()

    expense.project_id = 2897
    expense.save()

    mapping_setting = MappingSetting.objects.filter(
        workspace_id=2).first()
    mapping_setting.destination_field = 'DEPARTMENT'
    mapping_setting.source_field = 'PROJECT'
    mapping_setting.save()

    department_id = get_department_id_or_none(expense_group, expense)
    assert department_id == None

    mapping_setting.source_field = 'KLASS'
    mapping_setting.save()

    department_id = get_department_id_or_none(expense_group, expense)
    assert department_id == None

    department_id = get_department_id_or_none(expense_group, None)
    assert department_id == None


def test_get_ccc_account_id(db, mocker):
    configuration = Configuration.objects.get(workspace_id=49)
    configuration.map_fyle_cards_netsuite_account = True
    configuration.save()

    general_mappings = GeneralMapping.objects.get(workspace_id=49) 
    expense_group = ExpenseGroup.objects.get(id=47)

    expense = expense_group.expenses.first()
    expense.corporate_card_id = ExpenseAttribute.objects.filter(attribute_type='CREDIT_CARD_ACCOUNT').first().id
    expense.save()

    mapping = Mapping.objects.filter(workspace_id=2, source_type='COST_CENTER').first()
    mapping.source_type = 'CORPORATE_CARD'
    mapping.destination_type = 'CREDIT_CARD_ACCOUNT'
    mapping.source = ExpenseAttribute.objects.filter(attribute_type='CREDIT_CARD_ACCOUNT').first()
    mapping.workspace = Workspace.objects.get(id=49)
    mapping.save()

    get_ccc_account_id(configuration, general_mappings, expense, expense_group.description)

    configuration.map_fyle_cards_netsuite_account = False
    configuration.save()

    get_ccc_account_id(configuration, general_mappings, expense, expense_group.description)


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
def test_get_report_or_expense_number():
    expense_group = ExpenseGroup.objects.get(id=1)
    report_number =  get_report_or_expense_number(expense_group)
    assert report_number == 'C/2021/11/R/5'

    #For CCC
    expense_group = ExpenseGroup.objects.get(id=4)
    report_number =  get_report_or_expense_number(expense_group)
    assert report_number == 'E/2021/11/T/2'

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
    assert bill.subsidiary_id == '1'

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

    assert bill.currency == '1'
    assert bill.transaction_date <= datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    assert bill.subsidiary_id == '1'


def test_create_expense_report(db, mocker):

    expense_group = ExpenseGroup.objects.get(id=1)
    general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
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

    general_mappings.use_employee_department = True
    general_mappings.use_employee_location = True
    general_mappings.use_employee_class = True
    general_mappings.department_level = 'ALL'
    general_mappings.location_level = 'ALL'
    general_mappings.save()

    expense_group = ExpenseGroup.objects.get(id=2)

    expense_report = ExpenseReport.create_expense_report(expense_group)
    expense_report_lineitems = ExpenseReportLineItem.create_expense_report_lineitems(expense_group, configuration)
    
    for expense_report_lineitem in expense_report_lineitems:
        assert expense_report_lineitem.category == '13'
        assert expense_report_lineitem.amount == 100.0
    
    assert expense_report.currency == '1'

    
def test_get_class_id_or_none(db, add_fyle_credentials, mocker):
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.get_by_id',
        return_value={'options': ['samp'], 'updated_at': '2020-06-11T13:14:55.201598+00:00', 'is_mandatory': True}
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.post',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.sync',
        return_value=None
    )
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expense_group.description.update({'klass': 'sdfghjk'})
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

    mapping_setting.source_field = 'KLASS'
    mapping_setting.save()
    
    class_id = get_class_id_or_none(expense_group, expenses[0])
    assert class_id == None

    class_id = get_class_id_or_none(expense_group, None)
    assert class_id == None


def test_get_location_id_or_none(db, add_fyle_credentials, mocker):
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.get_by_id',
        return_value={'options': ['samp'], 'updated_at': '2020-06-11T13:14:55.201598+00:00', 'is_mandatory': True}
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.post',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.sync',
        return_value=None
    )
    expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
    expense_group.description.update({'klass': 'sdfghjk'})
    expense_group.save()
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

    mapping_setting.source_field = 'KLASS'
    mapping_setting.save()
    
    location_id = get_location_id_or_none(expense_group, expenses[0])
    assert location_id == None

    location_id = get_location_id_or_none(expense_group, None)
    assert location_id == None


def test_get_custom_segments(db, mocker):
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.get_by_id',
        return_value={'is_mandatory': True}
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.post',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.sync',
        return_value=None
    )
    expense_group = ExpenseGroup.objects.filter(workspace_id=2).first()
    expense_group.description.update({'klass': 'sdfghjk'})
    expenses = expense_group.expenses.all()

    mapping_settings = MappingSetting.objects.filter(workspace_id=2)
    for mapping_setting in mapping_settings:
        mapping_setting.destination_field = 'KLASS'
        mapping_setting.source_field = 'COST_CENTER'
        mapping_setting.save()
    
    custom_segments = get_custom_segments(expense_group, expenses[0])

    mapping_setting.source_field = 'PROJECT'
    mapping_setting.save()
    
    custom_segments = get_custom_segments(expense_group, expenses[0])

    mapping_setting.source_field = 'KLASS'
    mapping_setting.save()

    mapping = Mapping.objects.filter(workspace_id=2, source_type='COST_CENTER').first()
    mapping.source = ExpenseAttribute.objects.filter(workspace_id=2, attribute_type='KLASS').first()
    mapping.source_type = 'KLASS'
    mapping.destination_type = 'KLASS'
    mapping.save()

    custom_segments = get_custom_segments(expense_group, expenses[0])
    assert custom_segments == [{'scriptId': 'custcol780', 'type': 'Select', 'value': '1017'}]


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

    expense_group = ExpenseGroup.objects.get(id=2)

    general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id) 
    general_mappings.use_employee_class = True
    general_mappings.use_employee_department = True
    general_mappings.department_level = 'ALL'
    general_mappings.use_employee_location = True
    general_mappings.location_level = 'ALL'
    general_mappings.default_ccc_account_id = 252
    general_mappings.save()

    credit_card = CreditCardCharge.create_credit_card_charge(expense_group)
    configuration = Configuration.objects.get(workspace_id=1)
    credit_card_charge_lineitem = CreditCardChargeLineItem.create_credit_card_charge_lineitem(expense_group, configuration)

    assert credit_card_charge_lineitem.amount == 100.00
    assert credit_card_charge_lineitem.memo == 'ashwin.t@fyle.in - Accounts Payable - 2021-11-15 - C/2021/11/R/6 - '
    assert credit_card_charge_lineitem.billable == False

    assert credit_card.currency == '1'
    assert credit_card.transaction_date <= datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    assert credit_card.subsidiary_id == '1'

def test_support_post_date_integrations(mocker, db):
    workspace_id = 1

    #Import assert

    payload = fyle_expense_data['expenses']
    expense_id = fyle_expense_data['expenses'][0]['id']
    Expense.create_expense_objects(payload, 1)
    expense_objects = Expense.objects.get(expense_id=expense_id)
    expense_objects.reimbursable = False
    expense_objects.fund_source = 'CCC'
    expense_objects.source_account_type = 'PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT'
    expense_objects.save()
    assert expense_objects.posted_at.strftime("%m/%d/%Y") == '12/22/2021'

    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    expense_group_settings.corporate_credit_card_expense_group_fields = ['expense_id', 'employee_email', 'project', 'fund_source', 'posted_at']
    expense_group_settings.ccc_export_date_type = 'posted_at'
    expense_group_settings.save()
    
    field = ExpenseAttribute.objects.filter(workspace_id=workspace_id, attribute_type='PROJECT').last()
    field.attribute_type = 'KILLUA'
    field.save()

    configuration = Configuration.objects.get(workspace_id=1)

    ExpenseGroup.create_expense_groups_by_report_id_fund_source([expense_objects], configuration, 1)

    expense_groups = ExpenseGroup.objects.filter(workspace=1)
    assert expense_groups[2].description['posted_at'] == '2021-12-22T07:30:26'
    
    mapping_setting = MappingSetting(
        source_field='CATEGORY',
        destination_field='ACCOUNT',
        workspace_id=workspace_id,
        import_to_fyle=False,
        is_custom=False
    )
    mapping_setting.save()

    destination_attribute = DestinationAttribute.objects.create(
        attribute_type='ACCOUNT',
        display_name='Account',
        value='Concreteworks Studio',
        destination_id=321,
        workspace_id=workspace_id,
        active=True,
    )
    destination_attribute.save()
    expense_attribute = ExpenseAttribute.objects.create(
        attribute_type='CATEGORY',
        display_name='Category',
        value='Accounts Payablee',
        source_id='253737',
        workspace_id=workspace_id,
        active=True
    )
    expense_attribute.save()
    mapping = Mapping.objects.create(
        source_type='CATEGORY',
        destination_type='ACCOUNT',
        destination_id=destination_attribute.id,
        source_id=expense_attribute.id,
        workspace_id=workspace_id
    )
    mapping.save()

    mocker.patch(
        'netsuitesdk.api.vendor_bills.VendorBills.post',
        return_value=data['creation_response']
    )
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.search',
        return_value={}
    )
    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.get_or_create_employee',
        return_value=DestinationAttribute.objects.get(value='James Bond')
    )
    mocker.patch(
        'apps.netsuite.tasks.load_attachments',
        return_value='https://aaa.bbb.cc/x232sds'
    )
    task_log = TaskLog.objects.first()
    task_log.workspace_id = 1
    task_log.status = 'READY'
    task_log.save()

    configuration = Configuration.objects.get(workspace_id=workspace_id)
    configuration.auto_map_employees = 'EMAIL'
    configuration.auto_create_destination_entity = True
    configuration.save()

    LastExportDetail.objects.create(workspace_id=1, export_mode='MANUAL', total_expense_groups_count=2, 
    successful_expense_groups_count=0, failed_expense_groups_count=0, last_exported_at='2023-07-07 11:57:53.184441+00', 
    created_at='2023-07-07 11:57:53.184441+00', updated_at='2023-07-07 11:57:53.184441+00')
    
    expense_group = ExpenseGroup.objects.filter(workspace_id=workspace_id, fund_source='CCC').first()
    expense_group.description['posted_at'] = '2021-12-22T07:30:26'
    create_bill(expense_group, task_log.id, True)
    
    task_log = TaskLog.objects.get(pk=task_log.id)
    bill = Bill.objects.get(expense_group_id=expense_group.id)

    assert task_log.status=='COMPLETE'
    assert bill.currency == '1'
    assert bill.accounts_payable_id == '25'
    assert bill.entity_id == '1674'
    assert bill.transaction_date.strftime("%m/%d/%Y") == expense_objects.posted_at.strftime("%m/%d/%Y")

    