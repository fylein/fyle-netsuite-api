from rest_framework.test import APITestCase, APIClient

from apps.mappings.models import SubsidiaryMapping, GeneralMapping
from fyle_netsuite_api.test_utils import TestUtils


class TestModels(APITestCase):

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

    def test_subsidiary_mapping_creation(self):
        subsidiary_mappings = self.subsidiary_mappings
        self.assertEqual(subsidiary_mappings.subsidiary_name, 'Test Subsidiary', msg='Create Subsidiary Mapping Failed')
        self.assertEqual(subsidiary_mappings.internal_id, 1, msg='Create Subsidiary Mappings Failed')

    def test_general_mappings_creation(self):
        general_mappings = self.general_mappings
        self.assertEqual(general_mappings.location_id, 1, msg='Create General Mappings Failed')
        self.assertEqual(general_mappings.department_level, 'ALL', msg='Create General Mappings Failed')
