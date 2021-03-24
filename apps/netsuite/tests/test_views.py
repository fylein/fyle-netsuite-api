import os

from django.urls import reverse

from rest_framework.test import APITestCase, APIClient

from apps.mappings.models import SubsidiaryMapping
from apps.workspaces.models import NetSuiteCredentials
from fyle_netsuite_api.test_utils import TestUtils


class TestViews(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

        self.subsidiary_mappings = SubsidiaryMapping.objects.create(
            subsidiary_name='Test Subsidiary',
            internal_id=1,
            workspace_id=self.workspace.id
        )

        self.netsuite_credentials = NetSuiteCredentials.objects.create(
            ns_account_id=os.environ.get('NS_ACCOUNT_ID'),
            ns_consumer_key=os.environ.get('NS_CONSUMER_KEY'),
            ns_consumer_secret=os.environ.get('NS_CONSUMER_SECRET'),
            ns_token_id=os.environ.get('NS_TOKEN_ID'),
            ns_token_secret=os.environ.get('NS_TOKEN_SECRET'),
            workspace_id=self.workspace.id
        )

        self.custom_segment_payload = {
            'segment_type': 'CUSTOM_RECORD',
            'script_id': 'custcol780',
            'internal_id': '476'
        }

    def test_get_vendors_view(self):
        response = self.client.get(reverse('vendors', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Vendors Failed')

    def test_post_vendors_view(self):
        response = self.client.post(reverse('vendors', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Vendors Failed')

    def test_get_employees_view(self):
        response = self.client.get(reverse('employees', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Employees Failed')

    def test_post_employees_view(self):
        response = self.client.post(reverse('employees', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Employees Failed')

    def test_get_accounts_view(self):
        response = self.client.get(reverse('accounts', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Accounts Failed')

    def test_post_accounts_view(self):
        response = self.client.post(reverse('accounts', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Accounts Failed')

    def test_get_ccc_accounts_view(self):
        response = self.client.get(reverse('ccc-accounts', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET CCC Accounts Failed')

    def test_get_accounts_payables_view(self):
        response = self.client.get(reverse('accounts-payables', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Accounts Payable Failed')

    def test_get_vendor_payment_accounts_view(self):
        response = self.client.get(reverse('vendor-payment-accounts', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Vendor Payments Accounts Failed')

    def test_get_bank_accounts_view(self):
        response = self.client.get(reverse('bank-accounts', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Bank Accounts Failed')

    def test_get_credit_card_accounts_view(self):
        response = self.client.get(reverse('credit-card-accounts', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Credit Card Accounts Failed')

    def test_get_departments_view(self):
        response = self.client.get(reverse('departments', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Departments Failed')

    def test_post_departments_view(self):
        response = self.client.post(reverse('departments', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Departments Failed')

    def test_get_locations_view(self):
        response = self.client.get(reverse('locations', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Locations Failed')

    def test_post_locations_view(self):
        response = self.client.post(reverse('locations', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Locations Failed')

    def test_get_expense_categories_view(self):
        response = self.client.get(reverse('expense-categories', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Expense Categories Failed')

    def test_post_expense_categories_view(self):
        response = self.client.post(reverse('expense-categories', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Expense Categories Failed')

    def test_get_ccc_expense_categories_view(self):
        response = self.client.get(reverse('ccc-expense-categories', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET CCC Expense Categories Failed')

    def test_get_currencies_view(self):
        response = self.client.get(reverse('currencies', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Currencies Failed')

    def test_post_currencies_view(self):
        response = self.client.post(reverse('currencies', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Currencies Failed')

    def test_get_classifications_view(self):
        response = self.client.get(reverse('classifications', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Classifications Failed')

    def test_post_classifications_view(self):
        response = self.client.post(reverse('classifications', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Classifications Failed')

    def test_get_customers_view(self):
        response = self.client.get(reverse('customers', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Customers Failed')

    def test_post_customers_view(self):
        response = self.client.post(reverse('customers', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Customers Failed')

    def test_get_projects_view(self):
        response = self.client.get(reverse('projects', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Projects Failed')

    def test_post_projects_view(self):
        response = self.client.post(reverse('projects', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Projects Failed')

    def test_get_subsidiaries_view(self):
        response = self.client.get(reverse('subsidiaries', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Subsidiaries Failed')

    def test_get_custom_fields_view(self):
        response = self.client.get(reverse('custom-fields', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Custom Fields Failed')

    def test_post_custom_fields_view(self):
        response = self.client.post(reverse('custom-fields', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='POST Custom Fields Failed')

    def test_get_custom_segments_view(self):
        response = self.client.get(reverse('custom-segments', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Custom Segments Failed')

    def test_post_custom_segments_view(self):
        response = self.client.post(
            reverse('custom-segments', kwargs={'workspace_id': self.workspace.id}),
            headers={'Authorization': 'Bearer {}'.format(self.access_token)},
            data=self.custom_segment_payload
        )
        self.assertEqual(response.status_code, 200, msg='POST Custom Segments Failed')

    def get_get_netsuite_fields_view(self):
        response = self.client.post(reverse('netsuite-fields', kwargs={'workspace_id': self.workspace.id}),
                                    headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET NetSuite Fields Failed')
