import pytest
from datetime import datetime, timezone
from fylesdk import FyleSDK
from fyle_netsuite_api.tests import settings
from fyle_rest_auth.models import AuthToken, User
from apps.mappings.models import SubsidiaryMapping

from apps.workspaces.models import Workspace, NetSuiteCredentials, FyleCredential



@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': settings.DB_NAME,
        'HOST': settings.HOST,
    }

@pytest.fixture
def api_client():
   from rest_framework.test import APIClient
   return APIClient()

@pytest.fixture()
def test_connection():
    """
    Creates a connection with Fyle
    """
    client_id = settings.FYLE_CLIENT_ID
    client_secret = settings.FYLE_CLIENT_SECRET
    base_url = settings.FYLE_BASE_URL
    refresh_token = settings.FYLE_REFRESH_TOKEN


    fyle_connection = FyleSDK(
        base_url=base_url,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token
    )

    access_token = fyle_connection.access_token

    user_profile = fyle_connection.Employees.get_my_profile()['data']

    user = User(
        password='', last_login=datetime.now(tz=timezone.utc), id=1, email=user_profile['employee_email'],
        user_id=user_profile['user_id'], full_name='', active='t', staff='f', admin='t'
    )
    user.save()

    auth_token = AuthToken(
        id=1,
        refresh_token=refresh_token,
        user=user
    )
    auth_token.save()

    workspace = Workspace(
        id=1,
        name=user_profile['org_name'],
        fyle_org_id=user_profile['org_id'],
        ns_account_id=settings.NS_ACCOUNT_ID,
        last_synced_at=None,
        source_synced_at=None,
        destination_synced_at=None,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc)
    )
    workspace.save()
    workspace.user.add(user)


    fyle_credentials, _ = FyleCredential.objects.update_or_create(
        workspace_id=1,
        defaults={
            'refresh_token': settings.FYLE_REFRESH_TOKEN,
        }
    )

    fyle_credentials.save()


    subsidiary_mappings = SubsidiaryMapping(
        id=1,
        subsidiary_name='Test Subsidiary',
        internal_id=1,
        workspace_id=1
    )

    subsidiary_mappings.save()

    netsuite_credentials = NetSuiteCredentials(
        id=1,
        ns_account_id=settings.NS_ACCOUNT_ID,
        ns_consumer_key=settings.NS_CONSUMER_KEY,
        ns_consumer_secret=settings.NS_CONSUMER_SECRET,
        ns_token_id=settings.NS_TOKEN_ID,
        ns_token_secret=settings.NS_TOKEN_SECRET,
        workspace_id=workspace.id
    )

    netsuite_credentials.save()

    return fyle_connection
