import pytest
from django.test import TestCase
from datetime import datetime, timezone
from fyle_netsuite_api.tests import settings
from apps.workspaces.models import Workspace, NetSuiteCredentials, FyleCredential, \
    WorkspaceSchedule, Configuration
from fyle_rest_auth.models import AuthToken, User


@pytest.mark.django_db
def test_workspace_creation():
    '''
    Test Post of User Profile
    '''
    user = User.objects.get(id=1)

    new_workspace = Workspace.objects.create(
        id=100,
        name='Fyle Test Org',
        fyle_org_id='nil123pant',
        ns_account_id=settings.NS_ACCOUNT_ID,
        last_synced_at=None,
        source_synced_at=None,
        destination_synced_at=None,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc)
    )
    new_workspace.user.add(user)

    workspace = Workspace.objects.get(id=100)

    assert workspace.fyle_org_id=='nil123pant'
    assert workspace.name=='Fyle Test Org'
