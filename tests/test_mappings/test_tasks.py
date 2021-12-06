from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute
import pytest
from apps.mappings.tasks import create_fyle_projects_payload, create_fyle_tax_group_payload, remove_duplicates, create_fyle_categories_payload, construct_filter_based_on_destination
from .fixtures import data

def test_remove_duplicates(db):

    attributes = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE')
    assert len(attributes) == 35

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


def test_create_fyle_tax_group_payload(db):
    existing_tax_items_name = ExpenseAttribute.objects.filter(
        attribute_type='TAX_GROUP', workspace_id=2).values_list('value', flat=True)

    netsuite_attributes = DestinationAttribute.objects.filter(
        attribute_type='TAX_ITEM', workspace_id=2).order_by('value', 'id')

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_payload = create_fyle_tax_group_payload(
        netsuite_attributes, existing_tax_items_name)
    
    assert fyle_payload == []
        