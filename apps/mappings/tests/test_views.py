from django.urls import reverse

from rest_framework.test import APITestCase, APIClient

from apps.mappings.models import SubsidiaryMapping, GeneralMapping
from fyle_netsuite_api.test_utils import TestUtils


class TestViews(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

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

    def test_get_general_mappings_view(self):
        self.general_mappings = GeneralMapping.objects.create(
            location_name='Test',
            location_id=1,
            accounts_payable_name='APAccount',
            accounts_payable_id=1,
            default_ccc_account_name='CCAccount',
            default_ccc_account_id=1,
            reimbursable_account_name='ReimAccount',
            reimbursable_account_id=1,
            default_ccc_vendor_name='CCCVendor',
            default_ccc_vendor_id=1,
            vendor_payment_account_name='PayAccount',
            vendor_payment_account_id=1,
            location_level='ALL',
            department_level='ALL',
            use_employee_department=False,
            workspace_id=self.workspace.id
        )
        response = self.client.get(reverse('general-mappings', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET General Mappings Failed')

    def test_post_subsidiary_mappings_view(self):
        response = self.client.post(
            reverse('subsidiaries', kwargs={'workspace_id': self.workspace.id}),
            headers={'Authorization': 'Bearer {}'.format(self.access_token)},
            data=self.subsidiary_mappings_payload,
            format='json'
        )
        self.assertEqual(response.status_code, 200, msg='POST Subsidiary Mappings Failed')
