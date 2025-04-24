import pytest
from datetime import datetime, timezone
from fyle_rest_auth.models import User
from apps.users.helpers import get_cluster_domain_and_refresh_token
from fyle_netsuite_api.tests import settings
from fyle.platform import Platform
from apps.workspaces.models import FyleCredential


def test_get_cluster_domain_and_refresh_token(db, add_users_to_database):
    '''
    Test Post of User Profile
    '''
    client_id = settings.FYLE_CLIENT_ID
    client_secret = settings.FYLE_CLIENT_SECRET
    token_url = settings.FYLE_TOKEN_URI
    refresh_token = settings.FYLE_REFRESH_TOKEN
    server_url = 'https://staging.fyle.tech'

    fyle_connection = Platform(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        server_url=server_url
    )

    user_profile = fyle_connection.v1.spender.my_profile.get()['data']
    user = User(
        password='', last_login=datetime.now(tz=timezone.utc), id=1, email=user_profile['user']['email'],
        user_id=user_profile['user_id'], full_name='', active='t', staff='f', admin='t'
    )
    cluster_domain, refresh_token = get_cluster_domain_and_refresh_token(user)
    fyle_credentials = FyleCredential.objects.filter(workspace__user=user).first()

    assert cluster_domain == 'https://staging.fyle.tech'
    assert refresh_token == fyle_credentials.refresh_token

    fyle_credentials = FyleCredential.objects.filter(workspace__user=user)

    fyle_credentials.delete()
    cluster_domain, refresh_token = get_cluster_domain_and_refresh_token(user)

    assert cluster_domain == 'https://staging.fyle.tech'
    