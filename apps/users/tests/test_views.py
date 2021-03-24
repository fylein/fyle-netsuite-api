from django.urls import reverse

from rest_framework.test import APITestCase, APIClient

from fyle_netsuite_api.test_utils import TestUtils


class TestViews(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

    def test_get_profile_view(self):
        response = self.client.get(reverse('profile'), headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Profile Failed')

    def test_get_domain_view(self):
        response = self.client.get(reverse('domain'), headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Domain Failed')

    def test_get_orgs_view(self):
        response = self.client.get(reverse('orgs'), headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Orgs Failed')
