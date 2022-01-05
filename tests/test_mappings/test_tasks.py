import pytest
from django_q.models import Schedule
from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute

from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import NetSuiteCredentials
from apps.mappings.tasks import create_fyle_cost_centers_payload, create_fyle_expense_custom_field_payload, create_fyle_projects_payload, create_fyle_tax_group_payload, remove_duplicates, create_fyle_categories_payload, construct_filter_based_on_destination, schedule_categories_creation, schedule_cost_centers_creation, schedule_fyle_attributes_creation, sync_expense_categories_and_accounts, upload_categories_to_fyle
from .fixtures import data

def test_remove_duplicates(db):

    attributes = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE')
    assert len(attributes) == 34

    attributes = remove_duplicates(attributes)
    assert len(attributes) == 22


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
    assert cost_center_payload == data['cost_center_payload']

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

def test_sync_expense_categories_and_accounts(db, add_netsuite_credentials):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=1)
    existing_expense_category = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    
    existing_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=1).count()

    assert existing_expense_category == 34
    assert existing_accounts == 123

    sync_expense_categories_and_accounts('EXPENSE REPORT', 'EXPENSE REPORT', netsuite_connection)

    expense_category_count = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert expense_category_count == 38

    sync_expense_categories_and_accounts('BILL', 'JOURNAL ENTRY', netsuite_connection)

    count_of_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=1).count()
    assert count_of_accounts == 164


def test_upload_categories_to_fyle(db, add_fyle_credentials, add_netsuite_credentials):
    # will uncomment after post of categories is fixed
    # netsuite_attributes = upload_categories_to_fyle(1, 'EXPENSE REPORT', 'BILL')

    expense_category_count = DestinationAttribute.objects.filter(
        attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()
    assert expense_category_count == 34

    count_of_accounts = DestinationAttribute.objects.filter(
        attribute_type='ACCOUNT', workspace_id=1).count()
    assert count_of_accounts == 123


def test_schedule_creation(db, add_fyle_credentials):

    schedule_categories_creation(True, 3)
    schedule = Schedule.objects.last()
    assert schedule.func == 'apps.mappings.tasks.auto_create_category_mappings'
    
    schedule_cost_centers_creation(True, 1)
    schedule = Schedule.objects.last()
    assert schedule.func == 'apps.mappings.tasks.auto_create_cost_center_mappings'
