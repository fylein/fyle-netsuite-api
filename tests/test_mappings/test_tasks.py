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

    assert len(fyle_category_payload) == len(data['fyle_category_payload'])


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
        attribute_type='PROJECT', workspace_id=1).values_list('value', flat=True)
    
    paginated_ns_attributes = DestinationAttribute.objects.filter(
            attribute_type='PROJECT', workspace_id=2).order_by('value', 'id')

    paginated_ns_attributes = remove_duplicates(paginated_ns_attributes)

    fyle_payload = create_fyle_projects_payload(
        paginated_ns_attributes, existing_project_names)
    
    assert fyle_payload == data['fyle_project_payload']


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

    assert existing_expense_category == 33
    assert existing_accounts == 123

    sync_expense_categories_and_accounts('EXPENSE REPORT', 'EXPENSE REPORT', netsuite_connection)

    expense_category_count = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert expense_category_count == 34

    sync_expense_categories_and_accounts('BILL', 'JOURNAL ENTRY', netsuite_connection)

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

    netsuite_attributes = upload_categories_to_fyle(49, 'EXPENSE REPORT', 'BILL')

    expense_category_count = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=49).count()

    assert expense_category_count == 36

    assert len(netsuite_attributes) == 36

    count_of_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=49).count()
    
    assert count_of_accounts == 137

    netsuite_attributes = upload_categories_to_fyle(49, 'BILL', 'BILL')
    
    assert len(netsuite_attributes) == 137


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

    netsuite_attributes = upload_categories_to_fyle(workspace_id=1, reimbursable_expenses_object='EXPENSE REPORT', corporate_credit_card_expenses_object='BILL')

    destination_attributes = filter_unmapped_destinations('EXPENSE_CATEGORY', netsuite_attributes)
    assert len(destination_attributes) == 33


def test_schedule_creation(db):

    schedule_categories_creation(True, 3)
    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_category_mappings',
        args='{}'.format(3),
    ).first()
    
    schedule_categories_creation(False, 3)
    schedule: Schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_category_mappings',
        args='{}'.format(3)
    ).first()
    assert schedule == None

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
        'fyle.platform.apis.v1beta.admin.Categories.list_all',
        return_value=fyle_data['get_all_categories']
    )

    response = auto_create_category_mappings(workspace_id=1)
    assert response == []

    mappings_count = CategoryMapping.objects.filter(workspace_id=1).count()
    assert mappings_count == 34

    configuration = Configuration.objects.get(workspace_id=49)
    configuration.reimbursable_expenses_object = 'BILL'
    configuration.save()

    response = auto_create_category_mappings(workspace_id=49)

    mappings_count = CategoryMapping.objects.filter(workspace_id=49).count()
    assert mappings_count == 53

    fyle_credentials = FyleCredential.objects.all()
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_category_mappings(workspace_id=1)
    assert response == None

    with mock.patch('apps.workspaces.models.FyleCredential.objects.get') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='wrong parameter error', response="wrong parameter error")
        response = auto_create_category_mappings(workspace_id=1)


def test_auto_create_project_mappings(db, mocker):

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
    response = auto_create_project_mappings(workspace_id=1)
    assert response == None

    projects = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT', mapping__isnull=False).count()
    mappings = Mapping.objects.filter(workspace_id=1, destination_type='PROJECT').count()

    assert mappings == projects

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_project_mappings(workspace_id=1)

    assert response == None

    with mock.patch('apps.netsuite.connector.NetSuiteConnector.sync_projects') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='wrong parameter error', response="wrong parameter error")
        response = auto_create_project_mappings(workspace_id=1)

        mock_call.side_effect = Exception()
        response = auto_create_project_mappings(workspace_id=1)


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
    assert employee_mappings == 43

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
    assert employee_mappings == 43


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


def test_schedule_vendors_as_merchants_creation(db):
    workspace_id=2
    schedule_vendors_as_merchants_creation(import_vendors_as_merchants=True, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_vendors_as_merchants',
        args='{}'.format(workspace_id),
    ).first()
    
    assert schedule.func == 'apps.mappings.tasks.auto_create_vendors_as_merchants'

    schedule_vendors_as_merchants_creation(import_vendors_as_merchants=False, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_vendors_as_merchants',
        args='{}'.format(workspace_id),
    ).first()

    assert schedule == None


@pytest.mark.django_db
def test_schedule_projects_creation():
    workspace_id=2
    schedule_projects_creation(import_to_fyle=True, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_project_mappings',
        args='{}'.format(workspace_id),
    ).first()
    
    assert schedule.func == 'apps.mappings.tasks.auto_create_project_mappings'

    schedule_projects_creation(import_to_fyle=False, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_project_mappings',
        args='{}'.format(workspace_id),
    ).first()

    assert schedule == None


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
    post_merchants(fyle_connection, 49, False)

    expense_attribute = ExpenseAttribute.objects.filter(attribute_type='MERCHANT', workspace_id=49).count()
    assert expense_attribute == 12
