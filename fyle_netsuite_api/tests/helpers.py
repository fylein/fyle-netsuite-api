from django.urls import reverse
from datetime import datetime, timezone
import pytest

from fyle_netsuite_api.tests import settings
from rest_framework.test import APITestCase, APIClient
from fyle_rest_auth.models import AuthToken, User
from fylesdk import FyleSDK

from apps.workspaces.models import Workspace

from pytest_postgresql import factories


access_token = None
workspace = None
auth_token = None
user = None
client = None
user_profile = None

@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': 'localhost',
        'NAME': 'netsuite',
    }

@pytest.fixture(scope='session')
def test_connection(django_db_blocker):
    """
    Creates a connection with Fyle
    """
    with django_db_blocker.unblock():
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

        return fyle_connection

@pytest.fixture
def get_user_workspace_id(db):
    """
    GET workspace_id of the user
    """
    client.credentials(HTTP_AUTHORIZATION='Bearer {0}'.format(access_token))

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
    return workspace
