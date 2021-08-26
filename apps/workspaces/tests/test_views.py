from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from apps.workspaces.tests.fixtures import create_netsuite_credential_object_payload, \
    create_configurations_object_payload
from fyle_netsuite_api.tests.helpers import TestHelpers


class TestViews(APITestCase):

    def setUp(self):
        test_helpers = TestHelpers()
        connection = test_helpers.test_connection()
        access_token = connection.access_token

        self.client = APIClient()
        test_helpers.client = self.client
        self.workspace = test_helpers.get_user_workspace_id()

        self.__headers = {
            'Authorization': 'Bearer {}'.format(access_token)
        }

    def test_get_workspace_detail(self):
        response = self.client.get(
            reverse(
                'workspace-by-id', kwargs={
                    'workspace_id': self.workspace.id
                }
            ),
            headers=self.__headers
        )
        self.assertEqual(response.status_code, 200, msg='GET Workspace Detail Failed')

    def test_post_netsuite_credentials(self):
        response = self.client.post(
            reverse(
                'post-netsuite-credentials', kwargs={
                    'workspace_id': self.workspace.id
                }
            ),
            headers=self.__headers,
            data=create_netsuite_credential_object_payload(self.workspace.id)
        )
        self.assertEqual(response.status_code, 200, msg='POST NetSuite Credentials Failed')

    def test_post_workspace_configurations(self):
        response = self.client.post(
            reverse(
                'workspace-configurations', kwargs={
                    'workspace_id': self.workspace.id
                }
            ),
            headers=self.__headers,
            data=create_configurations_object_payload(self.workspace.id)
        )
        self.assertEqual(response.status_code, 201, msg='POST Workspace Configurations Failed')
