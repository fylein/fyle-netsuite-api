from django.db import models
from django.db.models import JSONField
from django.contrib.postgres.fields import ArrayField

from fyle_accounting_library.fyle_platform.constants import IMPORTED_FROM_CHOICES

from apps.netsuite.models import Bill, ExpenseReport, JournalEntry, VendorPayment, CreditCardCharge
from apps.workspaces.models import Workspace
from apps.fyle.models import ExpenseGroup

from fyle_accounting_mappings.models import ExpenseAttribute


def get_default():
    return {
        'default': 'default value'
    }


def get_error_type_mapping(attribute_type: str) -> str:
    """
    Returns the error type string based on the attribute type.
    Defaults to 'CATEGORY_MAPPING' if the type is not explicitly mapped.
    """
    mapping = {
        'EMPLOYEE': 'EMPLOYEE_MAPPING',
        'CATEGORY': 'CATEGORY_MAPPING',
        'TAX_GROUP': 'TAX_MAPPING'
    }
    return mapping.get(attribute_type, 'CATEGORY_MAPPING')


TASK_TYPE = (
    ('CREATING_JOURNAL_ENTRY', 'CREATING_JOURNAL_ENTRY'),
    ('CREATING_EXPENSE_REPORT', 'CREATING_EXPENSE_REPORT'),
    ('CREATING_BILL', 'CREATING_BILL'),
    ('CREATING_VENDOR_PAYMENT', 'CREATING_VENDOR_PAYMENT'),
    ('FETCHING_EXPENSES', 'FETCHING_EXPENSES'),
    ('CREATING_CREDIT_CARD_CHARGE', 'CREATING_CREDIT_CARD_CHARGE'),
    ('CREATING_CREDIT_CARD_REFUND', 'CREATING_CREDIT_CARD_REFUND')
)

TASK_STATUS = (
    ('FATAL', 'FATAL'),
    ('COMPLETE', 'COMPLETE'),
    ('IN_PROGRESS', 'IN_PROGRESS'),
    ('FAILED', 'FAILED'),
    ('ENQUEUED', 'ENQUEUED')
)

ERROR_TYPE_CHOICES = (('EMPLOYEE_MAPPING', 'EMPLOYEE_MAPPING'), ('CATEGORY_MAPPING', 'CATEGORY_MAPPING'), ('TAX_MAPPING', 'TAX_MAPPING'), ('NETSUITE_ERROR', 'NETSUITE_ERROR'))

class TaskLog(models.Model):
    """
    Table to store task logs
    """
    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    type = models.CharField(max_length=50, choices=TASK_TYPE, help_text='Task type (FETCH_EXPENSES / CREATE_BILL)')
    task_id = models.CharField(max_length=255, null=True, help_text='Django Q task reference')
    expense_group = models.ForeignKey(ExpenseGroup, on_delete=models.PROTECT,
        null=True, help_text='Reference to Expense group', unique=True)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, help_text='Reference to Bill', null=True)
    expense_report = models.ForeignKey(ExpenseReport, on_delete=models.PROTECT, help_text='Reference to Expense Report',
        null=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.PROTECT,
        help_text='Reference to journal_entry', null=True)
    vendor_payment = models.ForeignKey(VendorPayment, on_delete=models.PROTECT, help_text='Reference to VendorPayment',
        null=True)
    credit_card_charge = models.ForeignKey(
        CreditCardCharge, on_delete=models.PROTECT, help_text='Reference to CC Charge', null=True)
    status = models.CharField(max_length=255, choices=TASK_STATUS, help_text='Task Status')
    detail = JSONField(help_text='Task response', null=True, default=get_default)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')
    triggered_by = models.CharField(max_length=255, help_text="Triggered by", null=True, choices=IMPORTED_FROM_CHOICES)

    class Meta:
        db_table = 'task_logs'


class Error(models.Model):
    """
    Table to store errors
    """
    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    type = models.CharField(max_length=50, choices=ERROR_TYPE_CHOICES, help_text='Error type')
    expense_group = models.ForeignKey(
        ExpenseGroup, on_delete=models.PROTECT, 
        null=True, help_text='Reference to Expense group'
    )
    mapping_error_expense_group_ids = ArrayField(base_field=models.IntegerField(), default=[], help_text='list of mapping expense group ids')
    expense_attribute = models.OneToOneField(
        ExpenseAttribute, on_delete=models.PROTECT,
        null=True, help_text='Reference to Expense Attribute'
    )
    repetition_count = models.IntegerField(help_text='repetition count for the error', default=0)
    is_resolved = models.BooleanField(default=False, help_text='Is resolved')
    error_title = models.CharField(max_length=255, help_text='Error title')
    error_detail = models.TextField(help_text='Error detail')
    is_parsed = models.BooleanField(default=False, help_text='is the error parsed')
    article_link = models.CharField(max_length=255, help_text='Error Help Article Link', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    def increase_repetition_count_by_one(self, is_created: bool):
        """
        Increase the repetition count by 1.
        """
        if not is_created:
            self.repetition_count += 1
            self.save()
    
    @staticmethod
    def get_or_create_error_with_expense_group(expense_group, expense_attribute):
        """
        Get or create an Error record and ensure that the expense_group.id
        is present in mapping_error_expense_group_ids (without duplicates).
        """
        error_type = get_error_type_mapping(expense_attribute.attribute_type)
        error_detail = f"{expense_attribute.display_name} mapping is missing"

        error, created = Error.objects.get_or_create(
            workspace_id=expense_group.workspace_id,
            expense_attribute=expense_attribute,
            defaults={
                'type': error_type,
                'error_detail': error_detail,
                'error_title': expense_attribute.value,
                'is_resolved': False,
                'mapping_error_expense_group_ids': [expense_group.id],
            }
        )

        if not created and expense_group.id not in error.mapping_error_expense_group_ids:
            error.mapping_error_expense_group_ids = list(set(error.mapping_error_expense_group_ids + [expense_group.id]))
            error.save(update_fields=['mapping_error_expense_group_ids'])
        return error, created

    class Meta:
        db_table = 'errors'
