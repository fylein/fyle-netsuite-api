import os
from datetime import datetime

from django.utils import timezone
from fyle_rest_auth.models import AuthToken, User
from fylesdk import FyleSDK

from apps.workspaces.models import Workspace
from fyle_netsuite_api import test_settings


class TestHelpers:

    def __init__(self):
        self.access_token = None
        self.workspace = None
        self.auth_token = None
        self.user = None
        self.client = None

    def test_connection(self):
        client_id = os.environ.get('FYLE_TEST_CLIENT_ID')
        client_secret = os.environ.get('FYLE_TEST_CLIENT_SECRET')
        base_url = test_settings.FYLE_BASE_URL
        refresh_token = os.environ.get('FYLE_TEST_REFRESH_TOKEN')

        fyle_connection = FyleSDK(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

        self.access_token = fyle_connection.access_token

        self.user = User(
            password='', last_login=datetime.now(tz=timezone.utc), id=1, email=os.environ.get('TEST_USER_EMAIL'),
            user_id=os.environ.get('TEST_USER_ID'), full_name='', active='t', staff='f', admin='t'
        )
        self.user.save()

        self.auth_token = AuthToken(
            id=1,
            refresh_token=refresh_token,
            user=self.user
        )
        self.auth_token.save()

        return fyle_connection

    def api_authentication(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        self.client.post('{0}/workspaces/'.format(test_settings.API_URL),
                         headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.workspace = Workspace.objects.get(user=self.user)
        return self.workspace
