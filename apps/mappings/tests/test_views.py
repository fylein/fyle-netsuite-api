from django.urls import reverse

from rest_framework.test import APITestCase, APIClient

from apps.mappings.models import SubsidiaryMapping
from fyle_netsuite_api.tests.helpers import TestHelpers


class TestViews(APITestCase):

    def setUp(self):
        self.connection = TestHelpers.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestHelpers.api_authentication(self)

        self.workspace = auth

        self.subsidiary_mappings_payload = {
            'subsidiary_name': 'Test Subsidiary',
            'internal_id': 1
        }

    def test_get_subsidiary_mapping_view(self):
        self.subsidiary_mappings = SubsidiaryMapping.objects.create(
            subsidiary_name='Test Subsidiary',
            internal_id=1,
            workspace_id=self.workspace.id
        )
        response = self.client.get(reverse('subsidiaries', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Subsidiary Mappings Failed')
