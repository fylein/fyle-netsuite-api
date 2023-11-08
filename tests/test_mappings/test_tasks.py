import logging
from apps.fyle.models import ExpenseGroup
import pytest
from unittest import mock
from django_q.models import Schedule
from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute, CategoryMapping, \
     Mapping, MappingSetting, EmployeeMapping
from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import Configuration, FyleCredential, NetSuiteCredentials
from apps.mappings.tasks import *
from fyle_integrations_platform_connector import PlatformConnector
from apps.mappings.models import GeneralMapping
from tests.test_netsuite.fixtures import data as netsuite_data
from tests.test_fyle.fixtures import data as fyle_data
from .fixtures import data
from fyle.platform.exceptions import WrongParamsError

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def test_resolve_expense_attribute_errors(db):
    workspace_id = 1
    expense_group = ExpenseGroup.objects.get(id=1)

    employee_attribute = ExpenseAttribute.objects.filter(
        value=expense_group.description.get('employee_email'),
        workspace_id=expense_group.workspace_id,
        attribute_type='EMPLOYEE'
    ).first()

    error, _ = Error.objects.update_or_create(
        workspace_id=expense_group.workspace_id,
        expense_attribute=employee_attribute,
        defaults={
            'type': 'EMPLOYEE_MAPPING',
            'error_title': employee_attribute.value,
            'error_detail': 'Employee mapping is missing',
            'is_resolved': False
        }
    )

    resolve_expense_attribute_errors('EMPLOYEE', workspace_id, 'EMPLOYEE')
    assert Error.objects.get(id=error.id).is_resolved == True

    error, _ = Error.objects.update_or_create(
        workspace_id=expense_group.workspace_id,
        expense_attribute=employee_attribute,
        defaults={
            'type': 'EMPLOYEE_MAPPING',
            'error_title': employee_attribute.value,
            'error_detail': 'Employee mapping is missing',
            'is_resolved': False
        }
    )

    resolve_expense_attribute_errors('EMPLOYEE', workspace_id, 'VENDOR')
    assert Error.objects.get(id=error.id).is_resolved == True


def test_disable_category_for_items_mapping(db ,mocker):
    workspace_id = 49
    configuration = Configuration.objects.filter(workspace_id=workspace_id).first()
    configuration.import_items = False
    configuration.save()

    # mocking all the sdk calls
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Categories.sync',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Categories.post_bulk',
        return_value=[]
    )
    mocker.patch(
        'netsuitesdk.api.expense_categories.ExpenseCategory.get_all_generator',
        return_value=[]
    )

    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.get_all_generator',
        return_value=[] 
    )

    mocker.patch(
        'netsuitesdk.api.items.Items.get_all_generator',
        return_value=[]
    )

    # adding test data to the database
    destination_attribute = DestinationAttribute.objects.create(
        attribute_type='ACCOUNT',
        display_name='Item',
        value='Concrete',
        destination_id=3,
        workspace_id=workspace_id,
        active=False
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

    disable_category_for_items_mapping(configuration)

    # Querying the database to check if the mapping is disabled
    expense_attribute = ExpenseAttribute.objects.get(id=expense_attribute.id)

    assert expense_attribute.active == False


def test_remove_duplicates(db):

    attributes = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE')
    assert len(attributes) == 32

    attributes = remove_duplicates(attributes)
    assert len(attributes) == 20


def test_create_fyle_category_payload(mocker, db):
    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Categories.list_all',
        return_value=fyle_data['get_all_categories']
    )

    netsuite_attributes = DestinationAttribute.objects.filter(
            workspace_id=1, attribute_type='ACCOUNT'
        )

    fyle_credentials = FyleCredential.objects.filter().first()
    platform = PlatformConnector(fyle_credentials)

    netsuite_attributes = remove_duplicates(netsuite_attributes)
    category_map = get_all_categories_from_fyle(platform=platform)

    fyle_category_payload = create_fyle_categories_payload(netsuite_attributes, category_map)
    assert len(fyle_category_payload) == 98

    expense_attributes = ExpenseAttribute.objects.filter(workspace_id=1, active=True, attribute_type='CATEGORY')
    fyle_category_payload = create_fyle_categories_payload([], {}, expense_attributes, 'EXPENSE_CATEGORY')
    assert len(fyle_category_payload) == 1


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("EXPENSE_CATEGORY", {'destination_expense_head__isnull': True}), 
        ("ACCOUNT", {'destination_account__isnull': True})
    ],
)
def test_construct_filter_based_on_destination(test_input, expected):
    filter = construct_filter_based_on_destination(test_input)
    assert filter == expected
    

def test_create_fyle_projects_payload(db):
    existing_project_names = ExpenseAttribute.objects.filter(
        attribute_type='PROJECT', workspace_id=2).values_list('value', flat=True)
    
    paginated_ns_attributes = DestinationAttribute.objects.filter(
            attribute_type='PROJECT', workspace_id=2).order_by('value', 'id')

    destination_attributes = DestinationAttribute.objects.get(workspace_id=2, value='Nilesh Pant')

    expense_attributes = ExpenseAttribute.objects.get(workspace_id=2, value=destination_attributes.value)
    expense_attributes.value = 'sample'
    expense_attributes.save()

    paginated_ns_attributes = remove_duplicates(paginated_ns_attributes)

    fyle_payload = create_fyle_projects_payload(
        paginated_ns_attributes, existing_project_names)

    assert fyle_payload[0]['name'] == data['fyle_project_payload'][0]['name']

    expense_attributes.value = 'Nilesh Pant'
    expense_attributes.save()
    expense_attributes = ExpenseAttribute.objects.filter(workspace_id=2, value='Nilesh Pant')

    mapping = Mapping.objects.get(source_type='PROJECT')
    mapping.workspace_id = 2
    mapping.source = expense_attributes.first()
    mapping.save()

    fyle_payload = create_fyle_projects_payload(
        projects=[], existing_project_names=[], updated_projects=expense_attributes)
    
    assert fyle_payload[0]['name'] == data['fyle_project_payload'][0]['name']


def test_create_cost_center_payload(db):
    existing_cost_center_names = ExpenseAttribute.objects.filter(
        attribute_type='COST_CENTER', workspace_id=1).values_list('value', flat=True)
    
    netsuite_attributes = DestinationAttribute.objects.filter(
            attribute_type='CLASS', workspace_id=1).order_by('value', 'id')
    
    netsuite_attributes = remove_duplicates(netsuite_attributes)

    cost_center_payload = create_fyle_cost_centers_payload(netsuite_attributes, existing_cost_center_names)
    assert cost_center_payload[0] == data['cost_center_payload'][0]

def test_create_fyle_tax_group_payload(db):
    existing_tax_items_name = ExpenseAttribute.objects.filter(
        attribute_type='TAX_GROUP', workspace_id=2).values_list('value', flat=True)

    netsuite_attributes = DestinationAttribute.objects.filter(
        attribute_type='TAX_ITEM', workspace_id=2).order_by('value', 'id')

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_payload = create_fyle_tax_group_payload(
        netsuite_attributes, existing_tax_items_name)
    
    assert fyle_payload == []
        
def test_create_fyle_expense_custom_field_payload(db, add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.filter().first()
    platform = PlatformConnector(fyle_credentials)

    netsuite_attributes = DestinationAttribute.objects.filter(
        attribute_type='ASHWINTEST1', workspace_id=49).order_by('value', 'id')
    
    netsuite_attributes = remove_duplicates(netsuite_attributes)

    payload = create_fyle_expense_custom_field_payload(netsuite_attributes, 49, 'ASHWINTEST1', platform)

    assert payload == data['expense_custom_field_payload']

def test_create_fyle_merchants_payload(db):
    existing_merchants_name = ExpenseAttribute.objects.filter(
        attribute_type='MERCHANT', workspace_id=2).values_list('value', flat=True)

    netsuite_attributes = DestinationAttribute.objects.filter(
        attribute_type='VENDOR', workspace_id=2).order_by('value', 'id')

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_payload = create_fyle_merchants_payload(
        netsuite_attributes, existing_merchants_name)
    assert len(fyle_payload) == 7


def test_sync_expense_categories_and_accounts(mocker, db):
    mocker.patch(
        'netsuitesdk.api.expense_categories.ExpenseCategory.get_all_generator',
        return_value=netsuite_data['get_all_expense_categories']
    )

    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.get_all_generator',
        return_value=netsuite_data['get_all_accounts']    
    )

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    existing_expense_category = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    
    existing_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=1).count()
    
    configuration = Configuration.objects.get(workspace_id=1)
    configuration.expense_report_expense_category = 'EXPENSE REPORT'
    configuration.corporate_credit_card_expenses_object = 'EXPENSE REPORT'
    configuration.import_categories = True
    configuration.save()

    assert existing_expense_category == 33
    assert existing_accounts == 123

    sync_expense_categories_and_accounts(configuration, netsuite_connection)

    expense_category_count = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert expense_category_count == 34

    configuration.expense_report_expense_category = 'BILL'
    configuration.corporate_credit_card_expenses_object = 'JOURNAL ENTRY'
    configuration.save()

    sync_expense_categories_and_accounts(configuration, netsuite_connection)

    count_of_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=1).count()
    assert count_of_accounts == 124


def test_upload_categories_to_fyle(mocker, db):
    mocker.patch('fyle_integrations_platform_connector.apis.Categories.post_bulk')
    
    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Categories.list_all',
        return_value=fyle_data['get_all_categories']
    )

    mocker.patch(
        'netsuitesdk.api.expense_categories.ExpenseCategory.get_all_generator',
        return_value=netsuite_data['get_all_expense_categories']
    )

    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.get_all_generator',
        return_value=netsuite_data['get_all_accounts']    
    )

    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=49)
    platform = PlatformConnector(fyle_credentials=fyle_credentials)

    configuration = Configuration.objects.filter(workspace_id=49).first()
    configuration.reimbursable_expenses_object = 'EXPENSE REPORT'
    configuration.employee_field_mapping = 'VENDOR'
    configuration.corporate_credit_card_expenses_object = 'BILL'
    configuration.import_categories = True
    configuration.save()

    netsuite_attributes = upload_categories_to_fyle(49, configuration, platform)

    expense_category_count = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=49).count()

    assert expense_category_count == 36

    assert len(netsuite_attributes) == 137

    count_of_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=49).count()
    
    assert count_of_accounts == 137

    configuration.employee_field_mapping = 'EMPLOYEE'
    configuration.reimbursable_expenses_object = 'BILL'
    configuration.corporate_credit_card_expenses_object = 'BILL'
    configuration.save()

    netsuite_attributes = upload_categories_to_fyle(49, configuration, platform)
    
    assert len(netsuite_attributes) == 36


def test_filter_unmapped_destinations(db, mocker):
    mocker.patch('fyle_integrations_platform_connector.apis.Categories.post_bulk')

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Categories.list_all',
        return_value=fyle_data['get_all_categories']
    )

    mocker.patch(
        'netsuitesdk.api.expense_categories.ExpenseCategory.get_all_generator',
        return_value=netsuite_data['get_all_expense_categories']
    )

    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.get_all_generator',
        return_value=netsuite_data['get_all_accounts']    
    )

    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=1)
    platform = PlatformConnector(fyle_credentials=fyle_credentials)

    configuration = Configuration.objects.filter(workspace_id=1).first()
    configuration.reimbursable_expenses_object = 'EXPENSE REPORT'
    configuration.corporate_credit_card_expenses_object = 'BILL'
    configuration.import_categories = True
    configuration.save()

    netsuite_attributes = upload_categories_to_fyle(workspace_id=1,configuration=configuration, platform=platform)

    destination_attributes = filter_unmapped_destinations('EXPENSE_CATEGORY', netsuite_attributes)
    assert len(destination_attributes) == 33


def test_schedule_creation(db):
    schedule_cost_centers_creation(True, 1)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_cost_center_mappings',
        args='{}'.format(1),
    ).first()
    assert schedule.func == 'apps.mappings.tasks.auto_create_cost_center_mappings'

    schedule_cost_centers_creation(False, 1)
    schedule: Schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_cost_center_mappings',
        args='{}'.format(1)
    ).first()
    assert schedule == None

def test_auto_create_category_mappings(db, mocker):
    mocker.patch('fyle_integrations_platform_connector.apis.Categories.post_bulk')

    mocker.patch(
        'netsuitesdk.api.expense_categories.ExpenseCategory.get_all_generator',
        return_value=netsuite_data['get_all_expense_categories']
    )

    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.get_all_generator',
        return_value=netsuite_data['get_all_accounts']    
    )

    mocker.patch(
        'netsuitesdk.api.items.Items.get_all_generator',
        return_value=netsuite_data['get_all_items']  
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Categories.list_all',
        return_value=fyle_data['get_all_categories']
    )

    configuration = Configuration.objects.filter(workspace_id=1).first()
    configuration.import_categories = True
    configuration.import_items = True
    configuration.save()

    response = auto_create_category_mappings(workspace_id=1)
    assert response == None

    mappings_count = CategoryMapping.objects.filter(workspace_id=1).count()
    assert mappings_count == 34

    configuration = Configuration.objects.get(workspace_id=49)
    configuration.reimbursable_expenses_object = 'BILL'
    configuration.save()

    destination_attribute = DestinationAttribute.objects.filter(
        destination_account__isnull=False,
        attribute_type='ACCOUNT',
        workspace_id=49
	).first()

    destination_attribute.active = False
    destination_attribute.save()

    configuration = Configuration.objects.filter(workspace_id=49).first()
    configuration.employee_field_mapping = 'VENDOR'
    configuration.import_categories = True
    configuration.save()

    response = auto_create_category_mappings(workspace_id=49)

    mappings_count = CategoryMapping.objects.filter(workspace_id=49).count()
    assert mappings_count == 53

    # Patents & Licenses - Exempted
    category = ExpenseAttribute.objects.filter(value='Patents & Licenses - Exempted', workspace_id = 49).first()

    assert category == None

    category = ExpenseAttribute.objects.filter(value='COGS - Sales - Included', workspace_id = 49).first()

    assert category != None
    assert category.value == 'COGS - Sales - Included'

    with mock.patch('apps.workspaces.models.FyleCredential.objects.get') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='wrong parameter error', response="wrong parameter error")
        response = auto_create_category_mappings(workspace_id=1)

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_category_mappings(workspace_id=1)
    assert response == None


def test_auto_create_project_mappings(db, mocker):
    workspace_id = 1

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Projects.post_bulk',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Projects.sync',
        return_value=[]
    )
    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.sync_projects',
        return_value=None
    )
    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.sync_customers',
        return_value=None
    )
    mocker.patch(
        'apps.mappings.tasks.create_fyle_projects_payload',
        return_value=data['fyle_project_payload']
    )

    mocker.patch(
        'netsuitesdk.api.customers.Customers.count',
        return_value=len(netsuite_data['get_all_projects'][0])
    )
    workspace_id = 1

    destination_attribute = DestinationAttribute.objects.filter(
        mapping__isnull=False,
        mapping__destination_type='PROJECT',
        attribute_type='PROJECT',
        workspace_id=workspace_id
	).first()

    destination_attribute.active = False
    destination_attribute.save()

    response = auto_create_project_mappings(workspace_id=workspace_id)
    assert response == None

    projects = DestinationAttribute.objects.filter(workspace_id=workspace_id, attribute_type='PROJECT', mapping__isnull=False).count()
    mappings = Mapping.objects.filter(workspace_id=workspace_id, destination_type='PROJECT').count()

    assert mappings == projects

    with mock.patch('apps.netsuite.connector.NetSuiteConnector.sync_projects') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='wrong parameter error', response="wrong parameter error")
        response = auto_create_project_mappings(workspace_id=1)

        mock_call.side_effect = Exception()
        response = auto_create_project_mappings(workspace_id=1)

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    fyle_credentials.delete()

    response = auto_create_project_mappings(workspace_id=workspace_id)
    assert response == None


def test_auto_create_cost_center_mappings(db, mocker):
    mocker.patch('fyle_integrations_platform_connector.apis.CostCenters.post_bulk')

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.CostCenters.list_all',
        return_value=fyle_data['get_all_cost_centers']
    )

    mocker.patch(
        'netsuitesdk.api.departments.Departments.get_all_generator',
        return_value=netsuite_data['get_all_departments']
    )
    
    response = auto_create_cost_center_mappings(workspace_id=1)
    assert response == None

    cost_center = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='DEPARTMENT').count()
    mappings = Mapping.objects.filter(workspace_id=1, source_type='COST_CENTER').count()

    assert cost_center == 13
    assert mappings == 3

    # Sales and Cross - Included
    category = ExpenseAttribute.objects.filter(value='Sales and Cross - Exempted', workspace_id = 1).first()

    assert category == None

    category = ExpenseAttribute.objects.filter(value='Sales and Cross - Included', workspace_id = 1).first()

    assert category != None
    assert category.value == 'Sales and Cross - Included'

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_cost_center_mappings(workspace_id=1)
    assert response == None

    with mock.patch('fyle_integrations_platform_connector.apis.CostCenters.sync') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='wrong parameter error', response="wrong parameter error")
        response = auto_create_cost_center_mappings(workspace_id=1)


def test_schedule_tax_group_creation(db):
    workspace_id=2
    schedule_tax_groups_creation(import_tax_items=True, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_tax_group_mappings',
        args='{}'.format(workspace_id),
    ).first()
    
    assert schedule.func == 'apps.mappings.tasks.auto_create_tax_group_mappings'

    schedule_tax_groups_creation(import_tax_items=False, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_tax_group_mappings',
        args='{}'.format(workspace_id),
    ).first()

    assert schedule == None


def test_auto_create_tax_group_mappings(mocker, db):
    mocker.patch('fyle_integrations_platform_connector.apis.TaxGroups.post_bulk')

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.TaxGroups.list_all',
        return_value=fyle_data['get_all_tax_groups']
    )

    mocker.patch(
        'netsuitesdk.api.tax_items.TaxItems.get_all_generator',
        return_value=netsuite_data['get_all_tax_items']    
    )

    mocker.patch(
        'netsuitesdk.api.tax_groups.TaxGroups.get_all_generator',
        return_value=netsuite_data['get_all_tax_groups']
    )

    tax_groups = DestinationAttribute.objects.filter(workspace_id=2, attribute_type='TAX_ITEM').count()
    mappings = Mapping.objects.filter(workspace_id=2, destination_type='TAX_ITEM').count()
    
    assert tax_groups == 26
    assert mappings == 9

    auto_create_tax_group_mappings(workspace_id=2)

    tax_groups = DestinationAttribute.objects.filter(workspace_id=2, attribute_type='TAX_ITEM').count()
    mappings = Mapping.objects.filter(workspace_id=2, destination_type='TAX_ITEM').count()
    assert mappings == 26

    mapping_settings = MappingSetting.objects.get(source_field='TAX_GROUP', workspace_id=2)
    mapping_settings.delete()

    auto_create_tax_group_mappings(workspace_id=2)

    with mock.patch('fyle_integrations_platform_connector.apis.TaxGroups.sync') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='wrong parameter error', response="wrong parameter error")
        auto_create_tax_group_mappings(workspace_id=2)
    

def test_schedule_fyle_attributes_creation(db, mocker):

    schedule_fyle_attributes_creation(49)

    mocker.patch(
            'fyle_integrations_platform_connector.apis.ExpenseCustomFields.post',
            return_value=[]
    )
    mocker.patch(
            'fyle_integrations_platform_connector.apis.ExpenseCustomFields.sync',
            return_value=[]
    )

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_create_custom_field_mappings',
        args='{}'.format(49),
    ).first()
    assert schedule.func == 'apps.mappings.tasks.async_auto_create_custom_field_mappings'

    async_auto_create_custom_field_mappings(49)

    mapping_settings = MappingSetting.objects.filter(
        is_custom=True, import_to_fyle=True, workspace_id=49
    ).first()
    mapping_settings.is_custom = False
    mapping_settings.save()

    schedule_fyle_attributes_creation(49)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_create_custom_field_mappings',
        args='{}'.format(49),
    ).first()
    assert schedule == None


def test_async_auto_map_employees(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.get_all_generator',
        return_value=netsuite_data['get_all_vendors']    
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=fyle_data['get_all_employees']
    )

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=netsuite_data['get_all_employees']    
    )
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get',
        return_value=netsuite_data['get_all_employees'][0][0]
    )

    async_auto_map_employees(1)

    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 1 

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.employee_field_mapping = 'VENDOR'
    configuration.save()

    async_auto_map_employees(1)

    vendors = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='VENDOR').count()
    assert vendors == 7


def test_schedule_auto_map_employees(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.get_all_generator',
        return_value=netsuite_data['get_all_vendors']    
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=fyle_data['get_all_employees']
    )

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=netsuite_data['get_all_employees']    
    )

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get',
        return_value=netsuite_data['get_all_employees'][0][0] 
    )
    configuration = Configuration.objects.get(workspace_id=1)
    configuration.auto_map_employees = 'NAME'
    configuration.save()

    schedule_auto_map_employees(employee_mapping_preference='NAME', workspace_id=1)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_employees',
        args='{}'.format(1),
    ).first()
    assert schedule.func == 'apps.mappings.tasks.async_auto_map_employees'

    schedule_auto_map_employees(employee_mapping_preference='', workspace_id=1)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_employees',
        args='{}'.format(1),
    ).first()
    assert schedule == None
    async_auto_map_employees(1)

    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 1


@pytest.mark.django_db
def test_schedule_auto_map_ccc_employees(db, mocker):
    workspace_id=2

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.auto_map_employees = 'NAME'
    configuration.save()

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=fyle_data['get_all_employees']
    )

    schedule_auto_map_ccc_employees(workspace_id=2)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_ccc_account',
        args='{0}'.format(workspace_id),
    ).first()
    assert schedule.func == 'apps.mappings.tasks.async_auto_map_ccc_account'

    general_mappings = GeneralMapping.objects.get(workspace_id=1)

    general_mappings.default_ccc_account_name = 'Aus Account'
    general_mappings.default_ccc_account_id = 228
    general_mappings.save()

    async_auto_map_ccc_account(workspace_id=1)
    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 42

    employee = ExpenseAttribute.objects.filter(value='included@fyleforqvd.com', workspace_id=1).first()

    assert employee != None
    assert employee.value == 'included@fyleforqvd.com'

    employee = ExpenseAttribute.objects.filter(value='excluded@fyleforqvd.com', workspace_id=1).first()

    assert employee == None

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.auto_map_employees = ''
    configuration.save()

    schedule_auto_map_ccc_employees(workspace_id=1)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_ccc_account',
        args='{}'.format(1),
    ).first()

    assert schedule == None


@pytest.mark.django_db
def test_async_auto_map_ccc_account(db, mocker):
    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=fyle_data['get_all_employees']
    )

    general_mappings = GeneralMapping.objects.get(workspace_id=1)

    general_mappings.default_ccc_account_name = 'Aus Account'
    general_mappings.default_ccc_account_id = 228
    general_mappings.save()

    async_auto_map_ccc_account(workspace_id=1)
    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 42


def test_auto_create_vendors_as_merchants(db, mocker):
    mocker.patch('fyle_integrations_platform_connector.apis.Merchants.post')

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.ExpenseFields.list_all',
        return_value=fyle_data['get_all_expense_fields']
    )
    
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.get_all_generator',
        return_value=netsuite_data['get_all_vendors']    
    )

    vendors = DestinationAttribute.objects.filter(workspace_id=49, attribute_type='VENDOR').count()
    expense_attribute = ExpenseAttribute.objects.filter(workspace_id=49, attribute_type='MERCHANT').count()
    assert vendors == 7
    assert expense_attribute == 0

    auto_create_vendors_as_merchants(workspace_id=49)
    
    vendors = DestinationAttribute.objects.filter(workspace_id=49, attribute_type='VENDOR').count()
    expense_attribute = ExpenseAttribute.objects.filter(workspace_id=49, attribute_type='MERCHANT').count()
    assert expense_attribute == 12
    assert vendors == 7

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_vendors_as_merchants(workspace_id=1)

    assert response == None

    with mock.patch('fyle_integrations_platform_connector.apis.Merchants.sync') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='wrong parameter error', response="wrong parameter error")
        response = auto_create_vendors_as_merchants(workspace_id=1)


def test_auto_create_expense_fields_mappings(db, mocker):
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.post',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.ExpenseCustomFields.sync',
        return_value=[]
    )
    workspace_id = 1
    auto_create_expense_fields_mappings(workspace_id, 'CREDIT_CARD_ACCOUNT', 'CREDIT_CARD_ACCOUNT')

    with mock.patch('fyle_integrations_platform_connector.apis.ExpenseCustomFields.post') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='wrong parameter error', response="wrong parameter error")
        auto_create_expense_fields_mappings(workspace_id, 'CREDIT_CARD_ACCOUNT', 'CREDIT_CARD_ACCOUNT')

        mock_call.side_effect = Exception()
        auto_create_expense_fields_mappings(workspace_id, 'CREDIT_CARD_ACCOUNT', 'CREDIT_CARD_ACCOUNT')


@pytest.mark.django_db
def test_post_merchants(db, mocker):
    mocker.patch('fyle_integrations_platform_connector.apis.Merchants.post')
    mocker.patch(
        'fyle.platform.apis.v1beta.admin.ExpenseFields.list_all',
        return_value=fyle_data['get_all_expense_fields']
    )

    fyle_credentials = FyleCredential.objects.all()
    fyle_credentials = FyleCredential.objects.get(workspace_id=49) 
    fyle_connection = PlatformConnector(fyle_credentials)
    post_merchants(fyle_connection, 49)

    expense_attribute = ExpenseAttribute.objects.filter(attribute_type='MERCHANT', workspace_id=49).count()
    assert expense_attribute == 12


def test_schedule_netsuite_employee_creation_on_fyle(db):
    workspace_id=1
    schedule_netsuite_employee_creation_on_fyle(import_netsuite_employees=True, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_netsuite_employees_on_fyle',
        args='{}'.format(workspace_id),
    ).first()
    
    assert schedule.func == 'apps.mappings.tasks.auto_create_netsuite_employees_on_fyle'

    schedule_netsuite_employee_creation_on_fyle(import_netsuite_employees=False, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_netsuite_employees_on_fyle',
        args='{}'.format(workspace_id),
    ).first()

    assert schedule == None


def test_auto_create_netsuite_employees_on_fyle(db, mocker):
    workspace_id = 1

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=netsuite_data['get_all_employees']    
    )
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get',
        return_value=netsuite_data['get_all_employees'][0][0]
    )
    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Departments.list_all',
        return_value=netsuite_data['get_departments']
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Employees.sync',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Departments.post',
        return_value=[]
    )
    mocker.patch(
      'fyle.platform.apis.v1beta.admin.Employees.invite_bulk',
      return_value=fyle_data['get_all_employees']
   )

    employees = DestinationAttribute.objects.filter(workspace_id=workspace_id, attribute_type='EMPLOYEE').count()
    expense_attribute = ExpenseAttribute.objects.filter(workspace_id=workspace_id, attribute_type='EMPLOYEE').count()
    assert employees == 7
    assert expense_attribute == 30

    auto_create_netsuite_employees_on_fyle(workspace_id=workspace_id)
    
    employees = DestinationAttribute.objects.filter(workspace_id=workspace_id, attribute_type='EMPLOYEE').count()
    expense_attribute = ExpenseAttribute.objects.filter(workspace_id=workspace_id, attribute_type='EMPLOYEE').count()
    assert employees == 13
    assert expense_attribute == 30

    with mock.patch('fyle_integrations_platform_connector.apis.Employees.sync') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='Some of the parameters are wrong', response='Some of the parameters are wrong')
        auto_create_netsuite_employees_on_fyle(workspace_id=workspace_id)

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    fyle_credentials.delete()

    auto_create_netsuite_employees_on_fyle(workspace_id=workspace_id)
