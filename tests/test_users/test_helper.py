import pytest
from datetime import datetime, timezone
from fyle_rest_auth.models import User
from apps.users.helpers import get_cluster_domain_and_refresh_token
from fyle_netsuite_api.tests import settings
from fylesdk import FyleSDK

@pytest.mark.django_db
def test_get_cluster_domain_and_refresh_token(add_users_to_database,add_fyle_credentials):
    '''
    Test Post of User Profile
    '''
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
    cluster_domain, refresh_token = get_cluster_domain_and_refresh_token(user)

    assert cluster_domain == 'https://staging.fyle.tech'
    assert refresh_token == settings.FYLE_REFRESH_TOKEN