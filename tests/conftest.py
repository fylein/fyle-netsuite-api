import os
from datetime import datetime, timezone
from unittest import mock
import pytest
from rest_framework.test import APIClient
from fyle_rest_auth.models import AuthToken, User
from fyle.platform import Platform

from apps.workspaces.models import NetSuiteCredentials, FyleCredential
from apps.fyle.helpers import get_access_token
from fyle_netsuite_api.tests import settings

def pytest_configure():
    os.system('sh ./tests/sql_fixtures/reset_db_fixtures/reset_db.sh')

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture()
def access_token(db):
    """
    Creates a connection with Fyle
    """

    client_id = settings.FYLE_CLIENT_ID
    client_secret = settings.FYLE_CLIENT_SECRET
    token_url = settings.FYLE_TOKEN_URI
    refresh_token = settings.FYLE_REFRESH_TOKEN
    final_access_token = get_access_token(refresh_token=refresh_token)

    fyle = Platform(
        server_url="https://staging.fyle.tech/platform/v1beta",
        token_url=token_url,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret
    )

    user_profile = fyle.v1beta.spender.my_profile.get()['data']['user']
    user = User(
        password='', last_login=datetime.now(tz=timezone.utc), id=1, email=user_profile['email'],
        user_id=user_profile['id'], full_name='', active='t', staff='f', admin='t'
    )

    user.save()

    auth_token = AuthToken(
        id=1,
        refresh_token=refresh_token,
        user=user
    )
    auth_token.save()

    return final_access_token

@pytest.fixture(autouse=True)
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

@pytest.fixture(autouse=True)
def add_fyle_credentials(db):
    workspaces = [1,2,49]
    for workspace_id in workspaces:
        FyleCredential.objects.create(
            refresh_token=settings.FYLE_REFRESH_TOKEN,
            workspace_id=workspace_id,
            cluster_domain='https://staging.fyle.tech'
        )

@pytest.fixture(scope="session", autouse=True)
def default_session_fixture(request):
    patched_1 = mock.patch(
        'netsuitesdk.internal.client.NetSuiteClient.connect_tba',
        return_value=None
    )
    patched_1.__enter__()

    # patched_1 = mock.patch(
    #     'netsuitesdk.internal.client.NetSuite.connect_tba',
    #     return_value=None
    # )

    def unpatch():
        patched_1.__exit__()

    request.addfinalizer(unpatch)
