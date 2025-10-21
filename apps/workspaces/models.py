"""
Workspace Models
"""
from functools import cache
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField

from django_q.models import Schedule
from django.db.models import JSONField
from fyle_accounting_mappings.mixins import AutoAddCreateUpdateInfoMixin
from fyle_accounting_library.fyle_platform.enums import CacheKeyEnum

User = get_user_model()


ONBOARDING_STATE_CHOICES = (
    ('CONNECTION', 'CONNECTION'),
    ('SUBSIDIARY', 'SUBSIDIARY'),
    ('MAP_EMPLOYEES', 'MAP_EMPLOYEES'),
    ('EXPORT_SETTINGS', 'EXPORT_SETTINGS'),
    ('IMPORT_SETTINGS', 'IMPORT_SETTINGS'),
    ('ADVANCED_CONFIGURATION', 'ADVANCED_CONFIGURATION'),
    ('COMPLETE', 'COMPLETE'),
)


def get_default_onboarding_state():
    return 'CONNECTION'

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
    ccc_last_synced_at = models.DateTimeField(help_text='Datetime when ccc expenses were pulled last', null=True)
    source_synced_at = models.DateTimeField(help_text='Datetime when source dimensions were pulled', null=True)
    destination_synced_at = models.DateTimeField(help_text='Datetime when destination dimensions were pulled', null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')
    employee_exported_at = models.DateTimeField(auto_now_add=True, help_text='Employee exported to Fyle at datetime')
    onboarding_state = models.CharField(max_length=50, choices=ONBOARDING_STATE_CHOICES, default=get_default_onboarding_state, help_text='Onboarding status of the workspace', null=True)

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
    is_expired = models.BooleanField(default=False, help_text='Marks if credentials are expired')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        db_table = 'netsuite_credentials'

    @staticmethod
    def get_active_netsuite_credentials(workspace_id: int) -> 'NetSuiteCredentials':
        """
        Get active NetSuite credentials
        :param workspace_id: Workspace ID
        :return: NetSuite credentials
        """
        return NetSuiteCredentials.objects.get(workspace_id=workspace_id, is_expired=False)


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
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model', related_name='workspace_schedules')
    enabled = models.BooleanField(default=False)
    start_datetime = models.DateTimeField(help_text='Datetime for start of schedule', null=True)
    interval_hours = models.IntegerField(null=True)
    error_count = models.IntegerField(null=True, help_text='Number of errors in export')
    additional_email_options = JSONField(default=list, help_text='Email and Name of person to send email', null=True)
    emails_selected = ArrayField(base_field=models.CharField(max_length=255), null=True, help_text='File IDs')
    is_real_time_export_enabled = models.BooleanField(default=False)
    schedule = models.OneToOneField(Schedule, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, null=True, help_text='Updated at datetime')

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

NAME_IN_JOURNAL_ENTRY = (
    ('MERCHANT', 'MERCHANT'),
    ('EMPLOYEE', 'EMPLOYEE')
)

def get_default_memo_fields():
    return ['employee_email', 'category', 'merchant', 'spent_on', 'report_number', 'purpose']


class Configuration(AutoAddCreateUpdateInfoMixin, models.Model):
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
        max_length=50, choices=REIMBURSABLE_EXPENSES_OBJECT_CHOICES, help_text='Reimbursable Expenses type', null=True
    )
    corporate_credit_card_expenses_object = models.CharField(
        max_length=50, choices=COPORATE_CARD_EXPENSES_OBJECT_CHOICES,
        help_text='Corporate Card Expenses type', null=True
    )
    import_categories = models.BooleanField(default=False, help_text='Auto import categories to Fyle')
    import_tax_items = models.BooleanField(default=False, help_text='Auto import tax items to Fyle')
    import_projects = models.BooleanField(default=False, help_text='Auto import projects to Fyle')
    import_vendors_as_merchants = models.BooleanField(default=False, help_text='Auto import vendors from netsuite as merchants to Fyle')
    import_netsuite_employees = models.BooleanField(default=False, help_text='Auto import employees from netsuite as employees to Fyle')
    change_accounting_period = models.BooleanField(default=True, help_text='Change the accounting period')
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
    map_fyle_cards_netsuite_account = models.BooleanField(default=True, help_text='Map Fyle Cards to Netsuite Account')
    memo_structure = ArrayField(
        base_field=models.CharField(max_length=100), default=get_default_memo_fields,
        help_text='list of system fields for creating custom memo'
    )
    import_items = models.BooleanField(default=False, help_text='Auto import Items to Fyle')
    auto_create_destination_entity = models.BooleanField(default=False, help_text='Auto create vendor / employee')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
    name_in_journal_entry = models.CharField(max_length=100, help_text='Name in jounral entry for ccc expense only', default='MERCHANT',choices=NAME_IN_JOURNAL_ENTRY)
    allow_intercompany_vendors = models.BooleanField(default=False, help_text='Allow intercompany vendors')
    je_single_credit_line = models.BooleanField(default=False, help_text='Journal Entry Single Credit Line')
    is_attachment_upload_enabled = models.BooleanField(default=True, help_text='Is Attachment upload enabled')
    import_classes_with_parent = models.BooleanField(default=False, help_text='Import classes with parent')
    skip_accounting_export_summary_post = models.BooleanField(default=False, help_text='Skip accounting export summary post')

    class Meta:
        db_table = 'configurations'


EXPORT_MODE_CHOICES = (
    ('MANUAL', 'MANUAL'),
    ('AUTO', 'AUTO')
)


class LastExportDetail(models.Model):
    """
    Table to store Last Export Details
    """
    id = models.AutoField(primary_key=True)
    last_exported_at = models.DateTimeField(help_text='Last exported at datetime', null=True)
    next_export = models.DateTimeField(help_text='next export datetime', null=True)
    export_mode = models.CharField(
        max_length=50, help_text='Mode of the export Auto / Manual', choices=EXPORT_MODE_CHOICES, null=True
    )
    total_expense_groups_count = models.IntegerField(help_text='Total count of expense groups exported', null=True)
    successful_expense_groups_count = models.IntegerField(help_text='count of successful expense_groups ', null=True)
    failed_expense_groups_count = models.IntegerField(help_text='count of failed expense_groups ', null=True)
    unmapped_card_count = models.IntegerField(help_text='count of unmapped card', default=0)
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        db_table = 'last_export_details'


class FeatureConfig(models.Model):
    """
    Table to store Feature configs
    """
    id = models.AutoField(primary_key=True)
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    export_via_rabbitmq = models.BooleanField(default=False, help_text='Enable export via rabbitmq')
    fyle_webhook_sync_enabled = models.BooleanField(default=False, help_text='Enable fyle attribute webhook sync')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    @classmethod
    def get_feature_config(cls, workspace_id: int, key: str):
        """
        Get cached feature config value for workspace
        Cache for 48 hours (172800 seconds)
        :param workspace_id: workspace id
        :param key: feature config key (export_via_rabbitmq, import_via_rabbitmq, fyle_webhook_sync_enabled)
        :return: Boolean value for the requested feature
        """
        cache_key_map = {
            'export_via_rabbitmq': CacheKeyEnum.FEATURE_CONFIG_EXPORT_VIA_RABBITMQ,
            'fyle_webhook_sync_enabled': CacheKeyEnum.FEATURE_CONFIG_FYLE_WEBHOOK_SYNC_ENABLED
        }

        cache_key_enum = cache_key_map.get(key)
        cache_key = cache_key_enum.value.format(workspace_id=workspace_id)
        cached_value = cache.get(cache_key)

        if cached_value is not None:
            return cached_value

        feature_config = cls.objects.get(workspace_id=workspace_id)
        value = getattr(feature_config, key)
        cache.set(cache_key, value, 172800)
        return value

    class Meta:
        db_table = 'feature_configs'
