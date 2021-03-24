from datetime import datetime

from django.utils import timezone
from rest_framework.test import APITestCase, APIClient

from apps.fyle.models import Expense, ExpenseGroup, Reimbursement
from fyle_netsuite_api.test_utils import TestUtils


class FyleTestModels(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

        self.expense = Expense.objects.create(
            employee_email='test@test.in',
            category='Food',
            expense_id='tx1234',
            expense_number='E/1010',
            claim_number='C/0101',
            amount=100,
            currency='INR',
            settlement_id='set1234',
            state='PAYMENT_PROCESSING',
            report_id='rp1234',
            expense_created_at=datetime.now(tz=timezone.utc),
            expense_updated_at=datetime.now(tz=timezone.utc),
            fund_source='PERSONAL'
        )

        self.reimbursement = Reimbursement.objects.create(
            settlement_id='set1234',
            reimbursement_id='reim1234',
            state='COMPLETE',
            created_at=datetime.now(tz=timezone.utc),
            workspace_id=self.workspace.id
        )

        self.expense_group = ExpenseGroup.objects.create(
            description={"report_id": "rpf5vQ3xnoYI", "fund_source": "PERSONAL", "employee_email": "test@test.in"},
            fund_source='PERSONAL',
            exported_at=datetime.now(tz=timezone.utc),
            workspace_id=self.workspace.id
        )

    def test_expense_creation(self):
        expense = self.expense
        self.assertEqual(expense.fund_source, 'PERSONAL', msg='Create Expense Failed')
        self.assertEqual(expense.amount, 100, msg='Create Expense Failed')

    def test_expense_group_creation(self):
        expense_group = self.expense_group
        self.assertEqual(expense_group.fund_source, 'PERSONAL', msg='Create Expense Groups Failed')

    def test_reimbursement_creation(self):
        reimbursement = self.reimbursement
        self.assertEqual(reimbursement.state, 'COMPLETE', msg='Create Reimbursements Failed')
        self.assertEqual(reimbursement.reimbursement_id, 'reim1234', msg='Create Workspace General Settings Failed')
