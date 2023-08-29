from datetime import datetime, timezone

from apps.netsuite.helpers import check_interval_and_sync_dimension, sync_dimensions
from fyle_accounting_mappings.models import DestinationAttribute
from apps.workspaces.models import NetSuiteCredentials, Workspace
from .fixtures import data


def test_check_interval_and_sync_dimension(db):

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=2)
    workspace = Workspace.objects.get(id=2)
    synced = check_interval_and_sync_dimension(workspace=workspace, netsuite_credentials=netsuite_credentials)
    assert synced == True

    workspace.source_synced_at = datetime.now(timezone.utc)
    synced = check_interval_and_sync_dimension(workspace=workspace, netsuite_credentials=netsuite_credentials)
    assert synced == False


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
    categoty_count = DestinationAttribute.objects.filter(attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()

    assert employee_count == 7
    assert project_count == 1086
    assert categoty_count == 33

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    sync_dimensions(netsuite_credentials, 1)

    employee_count = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1).count()
    project_count = DestinationAttribute.objects.filter(attribute_type='PROJECT', workspace_id=1).count()
    categoty_count = DestinationAttribute.objects.filter(attribute_type='EXPENSE_CATEGORY', workspace_id=1).count()

    assert 13 == 13
    assert project_count == 1087
    assert categoty_count == 34
