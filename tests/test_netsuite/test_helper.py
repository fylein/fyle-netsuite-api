from datetime import datetime, timezone
import pytest

from apps.netsuite.helpers import check_interval_and_sync_dimension, sync_dimensions
from fyle_accounting_mappings.models import DestinationAttribute
from apps.workspaces.models import NetSuiteCredentials, Workspace


def test_check_interval_and_sync_dimension(db, add_netsuite_credentials):

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=2)
    workspace = Workspace.objects.get(id=2)
    synced = check_interval_and_sync_dimension(workspace=workspace, netsuite_credentials=netsuite_credentials)
    assert synced == True

    workspace.source_synced_at = datetime.now(timezone.utc)
    synced = check_interval_and_sync_dimension(workspace=workspace, netsuite_credentials=netsuite_credentials)
    assert synced == False


def test_sync_dimensions(add_netsuite_credentials):
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

    assert employee_count == 12
    assert project_count == 1090
    assert categoty_count == 38
