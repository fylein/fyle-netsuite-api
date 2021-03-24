from rest_framework.test import APITestCase, APIClient

from apps.tasks.models import TaskLog
from fyle_netsuite_api.test_utils import TestUtils


class TestModels(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

        self.task_log = TaskLog.objects.create(
            type='CREATING_BILL',
            task_id=1,
            status='COMPLETE',
            detail='',
            bill_id=1,
            expense_report_id='',
            journal_entry_id='',
            vendor_payment_id='',
            expense_group_id=1,
            workspace_id=self.workspace.id,
        )

    def test_task_log_creation(self):
        task_log = self.task_log
        self.assertEqual(task_log.type, 'CREATING_BILL', msg='Create TaskLog Failed')
        self.assertEqual(task_log.bill_id, 1, msg='Create TaskLog Failed')
