import pytest

from apps.workspaces.models import Workspace
from apps.workspaces.models import Workspace, NetSuiteCredentials
from apps.netsuite.helpers import check_interval_and_sync_dimension

@pytest.fixture
def sync_netsuite_dimensions(django_db_setup, test_connection):
    workspace = Workspace.objects.get(id=1)
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    synced = check_interval_and_sync_dimension(workspace, netsuite_credentials)