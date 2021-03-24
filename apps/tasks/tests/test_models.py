from datetime import datetime

from django.utils import timezone

from rest_framework.test import APITestCase, APIClient

from apps.fyle.models import ExpenseGroup
from apps.netsuite.models import Bill
from apps.tasks.models import TaskLog
from fyle_netsuite_api.test_utils import TestUtils


class TestModels(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

        self.expense_group = ExpenseGroup.objects.create(
            id=1,
            description={"report_id": "rpf5vQ3xnoYI", "fund_source": "PERSONAL", "employee_email": "blob@blob.in"},
            fund_source='PERSONAL',
            exported_at=datetime.now(tz=timezone.utc),
            workspace_id=self.workspace.id
        )

        self.bill = Bill.objects.create(
            id=1,
            entity_id=2380,
            accounts_payable_id=25,
            subsidiary_id=1,
            location_id=7,
            currency=1,
            memo='Reimbursable expense by Blob',
            external_id='bill1, - blob@blob.in',
            expense_group_id=1,
            transaction_date=datetime.now(tz=timezone.utc),
            payment_synced=False,
            paid_on_netsuite=False,
        )

        self.task_log = TaskLog.objects.create(
            type='CREATING_BILL',
            task_id=1,
            status='COMPLETE',
            detail='',
            bill_id=self.bill.id,
            expense_report_id='',
            journal_entry_id='',
            vendor_payment_id='',
            expense_group_id=self.expense_group.id,
            workspace_id=self.workspace.id,
        )

    def test_task_log_creation(self):
        task_log = self.task_log
        self.assertEqual(task_log.type, 'CREATING_BILL', msg='Create TaskLog Failed')
        self.assertEqual(task_log.bill_id, 1, msg='Create TaskLog Failed')
