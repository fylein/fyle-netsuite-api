from datetime import datetime, timezone

from apps.netsuite.helpers import check_interval_and_sync_dimension, sync_dimensions
from fyle_accounting_mappings.models import DestinationAttribute
from apps.workspaces.models import NetSuiteCredentials, Workspace
from apps.netsuite.connector import parse_error_and_get_message
from .fixtures import data


def test_check_interval_and_sync_dimension(db):

    workspace = Workspace.objects.get(id=2)
    check_interval_and_sync_dimension(2)
    assert workspace.destination_synced_at is not None

    old_destination_synced_at = workspace.destination_synced_at

    # If interval between syncs is less than 1 day, destination_synced_at should not change
    workspace.source_synced_at = datetime.now(timezone.utc)
    check_interval_and_sync_dimension(2)
    assert old_destination_synced_at == workspace.destination_synced_at


def test_sync_dimensions(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.get_all_generator',
        return_value=data['get_all_vendors']    
    )

    mocker.patch(
        'netsuitesdk.api.projects.Projects.get_all_generator',
        return_value=data['get_all_projects']    
    )

    mocker.patch(
        'netsuitesdk.api.projects.Projects.count',
        return_value=len(data['get_all_projects'][0])
    )

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=data['get_all_employees']    
    )

    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.get_all_generator',
        return_value=data['get_all_accounts']    
    )

    mocker.patch(
        'netsuitesdk.api.expense_categories.ExpenseCategory.get_all_generator',
        return_value=data['get_all_expense_categories']
    )

    mocker.patch(
        'netsuitesdk.api.custom_segments.CustomSegments.get',
        return_value=data['get_custom_segment']
    )

    mocker.patch(
        'netsuitesdk.api.custom_record_types.CustomRecordTypes.get_all_by_id',
        return_value=data['get_custom_records_all']
    )

    mocker.patch(
        'netsuitesdk.api.custom_lists.CustomLists.get',
        return_value=data['get_custom_list']
    )

    mocker.patch(
        'netsuitesdk.api.subsidiaries.Subsidiaries.get_all_generator',
        return_value=data['get_all_subsidiaries']
    )

    mocker.patch('netsuitesdk.api.locations.Locations.get_all_generator')
    mocker.patch('netsuitesdk.api.currencies.Currencies.get_all')
    mocker.patch('netsuitesdk.api.classifications.Classifications.get_all_generator')
    mocker.patch('netsuitesdk.api.departments.Departments.get_all_generator')
    mocker.patch('netsuitesdk.api.customers.Customers.get_all_generator')
    mocker.patch('netsuitesdk.api.customers.Customers.count', return_value=0)
    mocker.patch('netsuitesdk.api.tax_items.TaxItems.get_all_generator')
    mocker.patch('netsuitesdk.api.tax_groups.TaxGroups.get_all_generator')

    
    employee_count = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1).count()
    project_count = DestinationAttribute.objects.filter(attribute_type='PROJECT', workspace_id=1).count()
    category_count = DestinationAttribute.objects.filter(attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()

    assert employee_count == 7
    assert project_count == 1086
    assert category_count == 33

    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=1)
    sync_dimensions(netsuite_credentials, 1)

    employee_count = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1).count()
    project_count = DestinationAttribute.objects.filter(attribute_type='PROJECT', workspace_id=1).count()
    category_count = DestinationAttribute.objects.filter(attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()

    assert employee_count == 13
    assert project_count == 1087
    assert category_count == 34


def test_parse_error_and_get_message():
    raw_responses = data['charge_card_error_raw_responses']

    for raw_response in raw_responses:
        message = parse_error_and_get_message(raw_response['text'])
        assert message == raw_response['message']
