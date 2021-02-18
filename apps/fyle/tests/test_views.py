import os
from datetime import datetime

from django.urls import reverse
from django.utils import timezone
from fyle_rest_auth.models import AuthToken, User
from fylesdk import FyleSDK
from rest_framework.test import APITestCase, APIClient

from apps.workspaces.models import Workspace
from fyle_netsuite_api import settings


class FyleTests(APITestCase):

    def setUp(self):
        client_id = os.environ.get('FYLE_TEST_CLIENT_ID')
        client_secret = os.environ.get('FYLE_TEST_CLIENT_SECRET')
        base_url = settings.FYLE_BASE_URL
        refresh_token = os.environ.get('FYLE_TEST_REFRESH_TOKEN')

        self.connection = FyleSDK(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        )

        self.access_token = self.connection.access_token

        self.user = User(password='', last_login=datetime.now(tz=timezone.utc), id=1, email='user_email',
                         user_id='user_id', full_name='', active='t', staff='f', admin='t')
        self.user.save()

        self.auth_token = AuthToken(
            id=1,
            refresh_token=refresh_token,
            user=self.user
        )
        self.auth_token.save()

        self.client = APIClient()
        self.api_authentication()

    def api_authentication(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        self.client.post('{0}/workspaces/'.format(settings.API_URL),
                         headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.workspace = Workspace.objects.first()

    def test_get_fyle_expense_groups(self):
        response = self.client.get(reverse('expense-groups', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Expense Groups Failed')

    def test_get_employees(self):
        response = self.client.get(reverse('employees', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Employees Failed')

    def test_get_categories(self):
        response = self.client.get(reverse('categories', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Categories Failed')

    def test_get_cost_centers(self):
        response = self.client.get(reverse('cost-centers', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Cost Centers Failed')

    def test_get_projects_view(self):
        response = self.client.get(reverse('projects', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Projects Failed')

    def test_get_expense_custom_fields_view(self):
        response = self.client.get(reverse('expense-custom-fields', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Expense Custom Fields Failed')

    def test_get_expense_fields_view(self):
        response = self.client.get(reverse('expense-fields', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Expense Fields Failed')

    def test_get_expense_group_settings(self):
        response = self.client.get(reverse('expense-group-settings', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Expense Group Settings Failed')

    def test_post_employees_view(self):
        response = self.client.post(reverse('employees', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Employees Failed')

    def test_post_categories_view(self):
        response = self.client.post(reverse('categories', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Categories Failed')

    def test_post_cost_centers_view(self):
        response = self.client.post(reverse('cost-centers', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Cost Centers Failed')

    def test_post_projects_view(self):
        response = self.client.post(reverse('projects', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Projects Failed')

    def test_post_expense_custom_fields_view(self):
        response = self.client.post(reverse('expense-custom-fields', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Expense Custom Fields Failed')

    def test_post_expense_fields_view(self):
        response = self.client.post(reverse('projects', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Expense Fields Failed')
