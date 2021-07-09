from django.urls import reverse

from rest_framework.test import APITestCase, APIClient

from fyle_netsuite_api.test_helpers import TestHelpers


class TestViews(APITestCase):

    def setUp(self):
        self.connection = TestHelpers.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestHelpers.api_authentication(self)

        self.workspace = auth

    def test_get_profile_view(self):
        response = self.client.get(reverse('profile'), headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Profile Failed')
