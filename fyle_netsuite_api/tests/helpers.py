"""
Helper module for running tests
"""
from datetime import datetime

from django.utils import timezone
from fyle_rest_auth.models import AuthToken, User
from fylesdk import FyleSDK

from apps.workspaces.models import Workspace
from fyle_netsuite_api.tests import settings


class TestHelpers:
    """
    Tests helper functions
    """

    def __init__(self):
        self.access_token = None
        self.workspace = None
        self.auth_token = None
        self.user = None
        self.client = None

    def test_connection(self):
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

        self.access_token = fyle_connection.access_token

        user_profile = fyle_connection.Employees.get_my_profile()['data']

        self.user = User(
            password='', last_login=datetime.now(tz=timezone.utc), id=1, email=user_profile['employee_email'],
            user_id=user_profile['user_id'], full_name='', active='t', staff='f', admin='t'
        )
        self.user.save()

        self.auth_token = AuthToken(
            id=1,
            refresh_token=refresh_token,
            user=self.user
        )
        self.auth_token.save()

        return fyle_connection

    def get_user_workspace_id(self):
        """
        GET workspace_id of the user
        """
        self.client.credentials(HTTP_AUTHORIZATION='Bearer {0}'.format(self.access_token))
        self.client.post('{0}/workspaces/'.format(settings.API_URL),
                         headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.workspace = Workspace.objects.get(user=self.user)
        return self.workspace
