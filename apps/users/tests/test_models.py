from rest_framework.test import APITestCase, APIClient

from apps.users.models import User
from fyle_netsuite_api.test_utils import TestUtils


class TestModels(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

        self.user = User.objects.create(
            id='7',
            email='test@test.in',
            user_id='user_id',
            full_name='Full Name',
            active=True,
            staff=True,
            admin=False,
        )

    def test_user_creation(self):
        user = self.user
        self.assertEqual(user.admin, False, msg='Create User Failed')
        self.assertEqual(user.email, 'test@test.in', msg='Create User Failed')
