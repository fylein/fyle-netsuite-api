"""
Workspace Models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField

from django_q.models import Schedule
from django.db.models import JSONField


User = get_user_model()


class Workspace(models.Model):
    """
    Workspace model
    """
    id = models.AutoField(primary_key=True, help_text='Unique Id to identify a workspace')
    name = models.CharField(max_length=255, help_text='Name of the workspace')
    user = models.ManyToManyField(User, help_text='Reference to users table')
    fyle_org_id = models.CharField(max_length=255, help_text='org id', unique=True)
    cluster_domain = models.CharField(max_length=255, help_text='Fyle Cluster Domain', null=True)
    ns_account_id = models.CharField(max_length=255, help_text='NetSuite account id')
    last_synced_at = models.DateTimeField(help_text='Datetime when expenses were pulled last', null=True)
    source_synced_at = models.DateTimeField(help_text='Datetime when source dimensions were pulled', null=True)
    destination_synced_at = models.DateTimeField(help_text='Datetime when destination dimensions were pulled', null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        db_table = 'workspaces'


class NetSuiteCredentials(models.Model):
    """
    Table to store NetSuite credentials
    """
    id = models.AutoField(primary_key=True)
    ns_account_id = models.CharField(max_length=255, help_text='NetSuite Account ID')
    ns_consumer_key = models.CharField(max_length=255, help_text='NetSuite Consumer Key')
    ns_consumer_secret = models.CharField(max_length=255, help_text='NetSuite Consumer Secret')
    ns_token_id = models.CharField(max_length=255, help_text='NetSuite Token ID')
    ns_token_secret = models.CharField(max_length=255, help_text='NetSuite Token Secret')
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        db_table = 'netsuite_credentials'


class FyleCredential(models.Model):
    """
    Table to store Fyle credentials
    """
    id = models.AutoField(primary_key=True)
    refresh_token = models.TextField(help_text='Stores Fyle refresh token')
    cluster_domain = models.CharField(max_length=255, help_text='Cluster Domain', null=True)
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        db_table = 'fyle_credentials'


class WorkspaceSchedule(models.Model):
    """
    Workspace Schedule
    """
    id = models.AutoField(primary_key=True, help_text='Unique Id to identify a schedule')
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    enabled = models.BooleanField(default=False)
    start_datetime = models.DateTimeField(help_text='Datetime for start of schedule', null=True)
    interval_hours = models.IntegerField(null=True)
    error_count = models.IntegerField(null=True, help_text='Number of errors in export')
    additional_email_options = JSONField(default=list, help_text='Email and Name of person to send email', null=True)
    emails_selected = ArrayField(base_field=models.CharField(max_length=255), null=True, help_text='File IDs')
    schedule = models.OneToOneField(Schedule, on_delete=models.PROTECT, null=True)

    class Meta:
        db_table = 'workspace_schedules'


EMPLOYEE_FIELD_MAPPING_CHOICES = (
    ('EMPLOYEE', 'EMPLOYEE'),
    ('VENDOR', 'VENDOR')
)

REIMBURSABLE_EXPENSES_OBJECT_CHOICES = (
    ('EXPENSE REPORT', 'EXPENSE REPORT'),
    ('JOURNAL ENTRY', 'JOURNAL ENTRY'),
    ('BILL', 'BILL')
)

COPORATE_CARD_EXPENSES_OBJECT_CHOICES = (
    ('EXPENSE REPORT', 'EXPENSE REPORT'),
    ('JOURNAL ENTRY', 'JOURNAL ENTRY'),
    ('BILL', 'BILL'),
    ('CREDIT CARD CHARGE', 'CREDIT CARD CHARGE')
)

AUTO_MAP_EMPLOYEE_CHOICES = (
    ('EMAIL', 'EMAIL'),
    ('NAME', 'NAME'),
    ('EMPLOYEE_CODE', 'EMPLOYEE_CODE'),
)


def get_default_memo_fields():
    return ['employee_email', 'category', 'merchant', 'spent_on', 'report_number', 'purpose']


class Configuration(models.Model):
    """
    Workspace General Settings
    """
    id = models.AutoField(primary_key=True, help_text='Unique Id to identify a workspace')
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    # TODO: remove null=True later
    employee_field_mapping = models.CharField(
        max_length=50, choices=EMPLOYEE_FIELD_MAPPING_CHOICES, help_text='Employee field mapping', null=True
    )
    reimbursable_expenses_object = models.CharField(
        max_length=50, choices=REIMBURSABLE_EXPENSES_OBJECT_CHOICES, help_text='Reimbursable Expenses type'
    )
    corporate_credit_card_expenses_object = models.CharField(
        max_length=50, choices=COPORATE_CARD_EXPENSES_OBJECT_CHOICES,
        help_text='Corporate Card Expenses type', null=True
    )
    import_categories = models.BooleanField(default=False, help_text='Auto import categories to Fyle')
    import_tax_items = models.BooleanField(default=False, help_text='Auto import tax items to Fyle')
    import_projects = models.BooleanField(default=False, help_text='Auto import projects to Fyle')
    import_vendors_as_merchants = models.BooleanField(default=False, help_text='Auto import vendors from netsuite as merchants to Fyle')
    change_accounting_period = models.BooleanField(default=False, help_text='Change the accounting period')
    sync_fyle_to_netsuite_payments = models.BooleanField(
        default=False, help_text='Auto Sync Payments from Fyle to Netsuite'
    )
    sync_netsuite_to_fyle_payments = models.BooleanField(
        default=False, help_text='Auto Sync Payments from NetSuite to Fyle'
    )
    auto_create_merchants = models.BooleanField(default=False, help_text='Auto Create Merchants for CC Charges')
    auto_map_employees = models.CharField(
        max_length=50, choices=AUTO_MAP_EMPLOYEE_CHOICES,
        help_text='Auto Map Employees type from NetSuite to Fyle', null=True
    )
    skip_cards_mapping = models.BooleanField(default=False, help_text='Skip cards mapping')
    map_fyle_cards_netsuite_account = models.BooleanField(default=True, help_text='Map Fyle Cards to Netsuite Account')
    memo_structure = ArrayField(
        base_field=models.CharField(max_length=100), default=get_default_memo_fields,
        help_text='list of system fields for creating custom memo'
    )
    auto_create_destination_entity = models.BooleanField(default=False, help_text='Auto create vendor / employee')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'configurations'
