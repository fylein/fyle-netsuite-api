from django.urls import reverse

from rest_framework.test import APITestCase, APIClient

from test_utils import TestUtils


class FyleTests(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

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
