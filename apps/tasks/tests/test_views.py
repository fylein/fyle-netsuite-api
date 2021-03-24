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

    def test_get_all_tasks_view(self):
        response = self.client.get(reverse('all-tasks', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Tasks Failed')
