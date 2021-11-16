import os
from datetime import datetime, timezone
import pytest
from rest_framework.test import APIClient
from fylesdk import FyleSDK
from fyle_rest_auth.models import AuthToken, User
from fyle_netsuite_api.tests import settings


def pytest_configure():
    os.system('sh ./reset_db.sh')

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
