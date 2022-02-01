import os
from datetime import datetime, timezone
import pytest
from rest_framework.test import APIClient
from fylesdk import FyleSDK
from fyle_rest_auth.models import AuthToken, User
from fyle_netsuite_api.tests import settings
from apps.workspaces.models import NetSuiteCredentials, FyleCredential


def pytest_configure():
    os.system('sh ./tests/sql_fixtures/reset_db_fixtures/reset_db.sh')

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture()
def test_connection(db):
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


@pytest.fixture()
def add_netsuite_credentials(db):

    workspaces = [1,2,49]
    for workspace_id in workspaces:
        NetSuiteCredentials.objects.create(
            ns_account_id=settings.NS_ACCOUNT_ID,
            ns_consumer_key=settings.NS_CONSUMER_KEY,
            ns_consumer_secret=settings.NS_CONSUMER_SECRET,
            ns_token_id=settings.NS_TOKEN_ID,
            ns_token_secret=settings.NS_TOKEN_SECRET,
            workspace_id=workspace_id
        )

@pytest.fixture()
def add_fyle_credentials(db):
    workspaces = [1,2,49]
    for workspace_id in workspaces:
        FyleCredential.objects.create(
            refresh_token=settings.FYLE_REFRESH_TOKEN,
            workspace_id=workspace_id,
            cluster_domain='https://staging.fyle.tech'
        )
