from asyncio.log import logger
import pytest
from django_q.models import Schedule
from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute, CategoryMapping, \
     Mapping, MappingSetting, EmployeeMapping
from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import Configuration, FyleCredential, NetSuiteCredentials
from apps.mappings.tasks import async_auto_create_custom_field_mappings, async_auto_map_employees, auto_create_category_mappings, auto_create_cost_center_mappings, auto_create_project_mappings, auto_create_tax_group_mappings, create_fyle_cost_centers_payload, create_fyle_expense_custom_field_payload, create_fyle_projects_payload, create_fyle_tax_group_payload, filter_unmapped_destinations, remove_duplicates, create_fyle_categories_payload, \
    construct_filter_based_on_destination, schedule_auto_map_employees, schedule_categories_creation, schedule_cost_centers_creation, schedule_fyle_attributes_creation, schedule_tax_groups_creation, sync_expense_categories_and_accounts, upload_categories_to_fyle, \
        create_fyle_merchants_payload, auto_create_vendors_as_merchants, schedule_vendors_as_merchants_creation, async_auto_map_ccc_account, schedule_auto_map_ccc_employees, schedule_projects_creation, auto_create_expense_fields_mappings, \
            post_merchants
from .fixtures import data
from fyle_integrations_platform_connector import PlatformConnector
from apps.mappings.models import GeneralMapping

def test_remove_duplicates(db):

    attributes = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE')
    assert len(attributes) == 32

    attributes = remove_duplicates(attributes)
    assert len(attributes) == 20


def test_create_fyle_category_payload(db):

    netsuite_attributes = DestinationAttribute.objects.filter(
            workspace_id=1, attribute_type='ACCOUNT'
        )

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_category_payload = create_fyle_categories_payload(netsuite_attributes, 2)

    assert fyle_category_payload == data['fyle_category_payload']


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
    

def test_create_fyle_project_payload(db):
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
        
def test_create_fyle_expense_custom_field_payload(db):
    netsuite_attributes = DestinationAttribute.objects.filter(
        attribute_type='ASHWINTEST1', workspace_id=49).order_by('value', 'id')
    
    netsuite_attributes = remove_duplicates(netsuite_attributes)

    payload = create_fyle_expense_custom_field_payload(netsuite_attributes, 49, 'ASHWINTEST1')
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


def test_sync_expense_categories_and_accounts(db, add_netsuite_credentials):
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
    assert expense_category_count == 38

    sync_expense_categories_and_accounts('BILL', 'JOURNAL ENTRY', netsuite_connection)

    count_of_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=1).count()
    assert count_of_accounts == 164


def test_upload_categories_to_fyle(mocker, db, add_fyle_credentials, add_netsuite_credentials):

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Categories.post_bulk',
        return_value='nilesh'
    )

    netsuite_attributes = upload_categories_to_fyle(1, 'EXPENSE REPORT', 'BILL')

    expense_category_count = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert expense_category_count == 38
    assert len(netsuite_attributes) == expense_category_count

    count_of_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=1).count()
    assert count_of_accounts == 164

    netsuite_attributes = upload_categories_to_fyle(1, 'BILL', 'BILL')
    
    assert len(netsuite_attributes) == count_of_accounts


def test_filter_unmapped_destinations(db, mocker, add_fyle_credentials, add_netsuite_credentials):

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Categories.post_bulk',
        return_value='nilesh'
    )

    netsutie_attribtues = upload_categories_to_fyle(workspace_id=1, reimbursable_expenses_object='EXPENSE REPORT', corporate_credit_card_expenses_object='BILL')

    destination_attributes = filter_unmapped_destinations('EXPENSE_CATEGORY', netsutie_attribtues)
    assert len(destination_attributes) == 37


def test_schedule_creation(db, add_fyle_credentials):

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


def test_auto_create_category_mappings(db, mocker, add_fyle_credentials, add_netsuite_credentials):
    fyle_credentials = FyleCredential.objects.all()
    mocker.patch(
            'fyle_integrations_platform_connector.apis.Categories.post_bulk',
            return_value=[]
        )

    response = auto_create_category_mappings(workspace_id=1)
    assert response == []

    mappings = CategoryMapping.objects.filter(workspace_id=1)
    assert len(mappings) == 39

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.reimbursable_expenses_object = 'BILL'
    configuration.save()

    response = auto_create_category_mappings(workspace_id=1)

    mappings = CategoryMapping.objects.filter(workspace_id=1)
    assert len(mappings) == 172

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_category_mappings(workspace_id=1)

    assert response == None


def test_auto_create_project_mappings(db, mocker, add_fyle_credentials, add_netsuite_credentials):

    mocker.patch(
            'fyle_integrations_platform_connector.apis.Projects.post_bulk',
            return_value=[]
        )
    
    response = auto_create_project_mappings(workspace_id=1)
    assert response == None

    projects = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='PROJECT').count()
    mappings = Mapping.objects.filter(workspace_id=1, destination_type='PROJECT').count()

    assert mappings == projects

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_project_mappings(workspace_id=1)

    assert response == None



def test_auto_create_cost_center_mappings(db, mocker, add_fyle_credentials, add_netsuite_credentials):
    
    mocker.patch(
            'fyle_integrations_platform_connector.apis.CostCenters.post_bulk',
            return_value=[]
        )
    
    response = auto_create_cost_center_mappings(workspace_id=1)
    assert response == None

    cost_center = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='DEPARTMENT').count()
    mappings = Mapping.objects.filter(workspace_id=1, source_type='COST_CENTER').count()

    assert cost_center == 12
    assert mappings == 12

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_cost_center_mappings(workspace_id=1)
    assert response == None


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


def test_auto_create_tax_group_mappings(db, mocker, add_fyle_credentials, add_netsuite_credentials):
    mocker.patch(
        'fyle_integrations_platform_connector.apis.TaxGroups.post_bulk',
        return_value=[]
    )

    tax_groups = DestinationAttribute.objects.filter(workspace_id=2, attribute_type='TAX_ITEM').count()
    mappings = Mapping.objects.filter(workspace_id=2, destination_type='TAX_ITEM').count()
    
    assert tax_groups == 26
    assert mappings == 9

    auto_create_tax_group_mappings(workspace_id=2)

    tax_groups = DestinationAttribute.objects.filter(workspace_id=2, attribute_type='TAX_ITEM').count()
    mappings = Mapping.objects.filter(workspace_id=2, destination_type='TAX_ITEM').count()
    assert mappings == 29

    mapping_settings = MappingSetting.objects.get(source_field='TAX_GROUP', workspace_id=2)
    mapping_settings.delete()

    auto_create_tax_group_mappings(workspace_id=2)
    

def test_schedule_fyle_attributes_creation(db, mocker, add_netsuite_credentials, add_fyle_credentials, ):

    schedule_fyle_attributes_creation(49)

    mocker.patch(
            'fyle_integrations_platform_connector.apis.ExpenseCustomFields.post',
            return_value=[]
    )

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_create_custom_field_mappings',
        args='{}'.format(49),
    ).first()
    assert schedule.func == 'apps.mappings.tasks.async_auto_create_custom_field_mappings'

    async_auto_create_custom_field_mappings(49)

    schedule_fyle_attributes_creation(2)
    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_create_custom_field_mappings',
        args='{}'.format(2),
    ).first()

    assert schedule == None


def test_async_auto_map_employees(db, add_netsuite_credentials, add_fyle_credentials):
    async_auto_map_employees(1)

    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 1 


def test_schedule_auto_map_employees(db, add_netsuite_credentials, add_fyle_credentials):

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
    assert employee_mappings == 1  #Todo: Will Fix this Later


@pytest.mark.django_db
def test_schedule_auto_map_ccc_employees(db, mocker, add_fyle_credentials, add_netsuite_credentials):
    workspace_id=2

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.auto_map_employees = 'NAME'
    configuration.save()

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
    assert employee_mappings == 30

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
def test_async_auto_map_ccc_account(db, mocker, add_fyle_credentials, add_netsuite_credentials):
    workspace_id=2

    general_mappings = GeneralMapping.objects.get(workspace_id=1)

    general_mappings.default_ccc_account_name = 'Aus Account'
    general_mappings.default_ccc_account_id = 228
    general_mappings.save()

    async_auto_map_ccc_account(workspace_id=1)
    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 30


def test_auto_create_vendors_as_merchants(db, mocker, add_fyle_credentials, add_netsuite_credentials):
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Merchants.post_bulk',
        return_value=[]
    )


    vendors = DestinationAttribute.objects.filter(workspace_id=49, attribute_type='VENDOR').count()
    expense_attribute = ExpenseAttribute.objects.filter(workspace_id=49, attribute_type='MERCHANT').count()
    assert vendors == 7
    assert expense_attribute == 0

    auto_create_vendors_as_merchants(workspace_id=49)
    
    vendors = DestinationAttribute.objects.filter(workspace_id=49, attribute_type='VENDOR').count()
    expense_attribute = ExpenseAttribute.objects.filter(workspace_id=49, attribute_type='MERCHANT').count()
    assert expense_attribute == 24
    assert vendors == 9

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = auto_create_vendors_as_merchants(workspace_id=1)

    assert response == None
    

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


def test_auto_create_expense_fields_mappings():
    try:
        response = auto_create_expense_fields_mappings(10, '', '')
    except:
        logger.error('Error while creating expense field')
    

@pytest.mark.django_db
def test_post_merchants(db, mocker, add_fyle_credentials, add_netsuite_credentials):
    fyle_credentials = FyleCredential.objects.all()
    fyle_credentials = FyleCredential.objects.get(workspace_id=49) 
    fyle_connection = PlatformConnector(fyle_credentials)
    post_merchants(fyle_connection, 49, False)

    expense_attribute = ExpenseAttribute.objects.filter(attribute_type='MERCHANT', workspace_id=49).count()
    assert expense_attribute == 24

