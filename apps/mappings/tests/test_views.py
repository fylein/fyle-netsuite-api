from django.urls import reverse

from rest_framework.test import APITestCase, APIClient

from apps.mappings.models import SubsidiaryMapping
from apps.mappings.tests.fixtures import create_subsidiary_mappings_payload
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

    def test_get_subsidiary_mapping_view(self):
        self.subsidiary_mappings = SubsidiaryMapping.objects.create(
            subsidiary_name='Test Subsidiary',
            internal_id=1,
            workspace_id=self.workspace.id
        )
        response = self.client.get(
            reverse(
                'subsidiaries', kwargs={
                    'workspace_id': self.workspace.id
                }
            ),
            headers=self.__headers
        )
        self.assertEqual(response.status_code, 200, msg='GET Subsidiary Mappings Failed')

    def test_post_subsidiary_mappings_view(self):
        response = self.client.post(
            reverse(
                'subsidiaries', kwargs={
                    'workspace_id': self.workspace.id
                }
            ),
            headers=self.__headers,
            data=create_subsidiary_mappings_payload(self.workspace.id)
        )
        self.assertEqual(response.status_code, 201, msg='POST Subsidiary Mappings Failed')
