from datetime import datetime

from django.utils import timezone
from rest_framework.test import APITestCase, APIClient

from apps.fyle.models import ExpenseGroup, Expense
from apps.netsuite.models import CustomSegment, Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem,\
    JournalEntry, JournalEntryLineItem, VendorPayment, VendorPaymentLineitem
from fyle_netsuite_api.test_utils import TestUtils


class TestModels(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

        self.custom_segment = CustomSegment.objects.create(
            name='FAVOURITE_BANDS',
            segment_type='CUSTOM_RECORD',
            script_id='custcol1',
            internal_id='1',
            workspace_id=self.workspace.id
        )

        self.expense = Expense.objects.create(
            id=1,
            employee_email='blob@blob.in',
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

        self.bill_line_item = BillLineitem.objects.create(
            id=1,
            account_id=84,
            location_id=1,
            department_id='',
            class_id='',
            amount=100,
            memo='Expense by blob@blob.in against category Food with claim number - C/R/4, purpose - food',
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            bill_id=1,
            expense_id=1,
            netsuite_custom_segments=[],
            billable='',
            customer_id='',
        )

        self.expense_report = ExpenseReport.objects.create(
            id=1,
            account_id=2,
            entity_id=2,
            currency=1,
            department_id='',
            class_id='',
            location_id=1,
            subsidiary_id=1,
            memo='Reimbursable expenses by Blob',
            external_id='report 5 - blob@blob.in',
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            expense_group_id=1,
            transaction_date=datetime.now(tz=timezone.utc),
            payment_synced=False,
            paid_on_netsuite=False,
        )

        self.expense_report_line_item = ExpenseReportLineItem.objects.create(
            id=1,
            amount=100,
            category=5,
            class_id='',
            customer_id='',
            location_id=1,
            department_id='',
            currency=1,
            memo='Expense by blob@blob.in against category Food with claim number - C/R/4, purpose - food',
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            expense_id=1,
            expense_report_id=1,
            transaction_date=datetime.now(tz=timezone.utc),
            netsuite_custom_segments=[],
            billable=''
        )

        self.journal_entry = JournalEntry.objects.create(
            id=1,
            currency=1,
            subsidiary_id=1,
            department_id='',
            memo='Reimbursable expenses by blob',
            external_id='journal398 - blob@blob.in',
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            expense_group_id=1,
            transaction_date=datetime.now(tz=timezone.utc),
            entity_id=1644,
            location_id='',
            payment_synced=False,
            paid_on_netsuite=False
        )

        self.journal_entry_line_item = JournalEntryLineItem.objects.create(
            id=1,
            debit_account_id=25,
            account_id=68,
            department_id='',
            location_id=1,
            class_id='',
            entity_id=1552,
            amount=100,
            memo='CARRABBAS',
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            expense_id=1,
            journal_entry_id=1,
            netsuite_custom_segments=''
        )

        self.vendor_payment = VendorPayment.objects.create(
            id=1,
            accounts_payable_id=185,
            account_id=2,
            entity_id=38,
            currency=1,
            department_id='',
            location_id='',
            class_id='',
            subsidiary_id=1,
            external_id='bill-blob-59',
            memo='Payment for bill by Blob',
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc)
        )

        self.vendor_payment_line_item = VendorPaymentLineitem.objects.create(
            id=1,
            doc_id=24420,
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            expense_group_id=1,
            vendor_payment_id=1
        )

    def test_custom_segment_creation(self):
        custom_segment = self.custom_segment
        self.assertEqual(custom_segment.name, 'FAVOURITE_BANDS', msg='Create CustomSegment Failed')
        self.assertEqual(custom_segment.segment_type, 'CUSTOM_RECORD', msg='Create CustomSegment Failed')

    def test_bill_creation(self):
        bill = self.bill
        self.assertEqual(bill.subsidiary_id, 1, msg='Create Bill Failed')
        self.assertEqual(bill.external_id, 'bill1, - blob@blob.in', msg='Create Bill Failed')

    def test_bill_line_item_creation(self):
        bill_line_item = self.bill_line_item
        self.assertEqual(bill_line_item.amount, 100, msg='Create BillLineItem Failed')
        self.assertEqual(bill_line_item.bill_id, 1, msg='Create BillLineItem Failed')

    def test_expense_report_creation(self):
        expense_report = self.expense_report
        self.assertEqual(expense_report.subsidiary_id, 1, msg='Create ExpenseReport Failed')
        self.assertEqual(expense_report.id, 1, msg='Create ExpenseReport Failed')

    def test_expense_report_line_item_creation(self):
        expense_report_line_item = self.expense_report_line_item
        self.assertEqual(expense_report_line_item.amount, 100, msg='Create ExpenseReportLineItem Failed')
        self.assertEqual(expense_report_line_item.id, 1, msg='Create ExpenseReportLineItem Failed')

    def test_journal_entry_creation(self):
        journal_entry = self.journal_entry
        self.assertEqual(journal_entry.subsidiary_id, 1, msg='Create JournalEntry Failed')
        self.assertEqual(journal_entry.id, 1, msg='Create JournalEntry Failed')

    def test_journal_entry_line_item_creation(self):
        journal_entry_line_item = self.journal_entry_line_item
        self.assertEqual(journal_entry_line_item.amount, 100, msg='Create JournalEntryLineItem Failed')
        self.assertEqual(journal_entry_line_item.id, 1, msg='Create JournalEntryLineItem Failed')

    def test_vendor_payment_creation(self):
        vendor_payment = self.vendor_payment
        self.assertEqual(vendor_payment.subsidiary_id, 1, msg='Create VendorPayment Failed')
        self.assertEqual(vendor_payment.id, 1, msg='Create VendorPayment Failed')

    def test_vendor_payment_line_item_creation(self):
        vendor_payment_line_item = self.vendor_payment_line_item
        self.assertEqual(vendor_payment_line_item.doc_id, 24420, msg='Create VendorPaymentLineItem Failed')
        self.assertEqual(vendor_payment_line_item.expense_group_id, 1, msg='Create VendorPaymentLineItem Failed')
