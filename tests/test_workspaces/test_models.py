import pytest
from django.test import TestCase
from datetime import datetime, timezone, timedelta
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

@pytest.mark.django_db(databases=['default'])
def test_netsuite_credentials_is_expired():
    # Clean up any existing credentials
    NetSuiteCredentials.objects.all().delete()

    workspace1 = Workspace.objects.create(
        name='Test Workspace 1',
        fyle_org_id='test_org1',
        cluster_domain='https://test.fyle.tech'
    )
    workspace2 = Workspace.objects.create(
        name='Test Workspace 2',
        fyle_org_id='test_org2',
        cluster_domain='https://test.fyle.tech'
    )

    credentials = NetSuiteCredentials.objects.create(
        workspace=workspace1,
        ns_account_id='test_account',
        ns_consumer_key='test_consumer_key',
        ns_consumer_secret='test_consumer_secret',
        ns_token_id='test_token_id',
        ns_token_secret='test_token_secret'
    )
    assert credentials.is_expired is False

    credentials.is_expired = True
    credentials.save()
    assert credentials.is_expired is True

    credentials2 = NetSuiteCredentials.objects.create(
        workspace=workspace2,
        ns_account_id='test_account2',
        ns_consumer_key='test_consumer_key2',
        ns_consumer_secret='test_consumer_secret2',
        ns_token_id='test_token_id2',
        ns_token_secret='test_token_secret2',
        is_expired=True
    )
    assert credentials2.is_expired is True

    expired_credentials = NetSuiteCredentials.objects.filter(is_expired=True)
    assert expired_credentials.count() == 2

    non_expired_credentials = NetSuiteCredentials.objects.filter(is_expired=False)
    assert non_expired_credentials.count() == 0

    credentials.is_expired = False
    credentials.save()
    assert credentials.is_expired is False
    assert NetSuiteCredentials.objects.filter(is_expired=False).count() == 1
