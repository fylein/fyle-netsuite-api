"""
@Sravan: Add what the module does
"""
import os
from datetime import datetime

from django.utils import timezone
from fyle_rest_auth.models import AuthToken, User
from fylesdk import FyleSDK

from apps.workspaces.models import Workspace
from fyle_netsuite_api.tests import settings


class TestHelpers:
    """
    @Sravan: Add what the class does
    """

    def __init__(self):
        """
        @Sravan: Add what the function does
        """
        self.access_token = None
        self.workspace = None
        self.auth_token = None
        self.user = None
        self.client = None

    def test_connection(self):
        """
        @Sravan: Add what the function does
        """
        client_id = os.environ.get('FYLE_TEST_CLIENT_ID')
        client_secret = os.environ.get('FYLE_TEST_CLIENT_SECRET')
        base_url = settings.FYLE_BASE_URL
        refresh_token = os.environ.get('FYLE_TEST_REFRESH_TOKEN')

        fyle_connection = FyleSDK(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

        self.access_token = fyle_connection.access_token

        # To do @Sravan: Use email and user id from my profile call
        user_profile = fyle_connection.Employees.get_my_profile()['data']

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

    # To do @Sravan: Rename the function to get_user_workspace_id()
    def api_authentication(self):
        """
        @Sravan: Add what the function does
        """
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)

        # To do @Sravan: To move this to workspace tests so that we can test workspace creation too
        self.client.post('{0}/workspaces/'.format(settings.API_URL),
                         headers={'Authorization': 'Bearer {}'.format(self.access_token)})

        # This bit can stay here
        self.workspace = Workspace.objects.get(user=self.user)
        return self.workspace
