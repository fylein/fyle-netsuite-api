"""
Workspace Models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django_q.models import Schedule

User = get_user_model()


class Workspace(models.Model):
    """
    Workspace model
    """
    id = models.AutoField(primary_key=True, help_text='Unique Id to identify a workspace')
    name = models.CharField(max_length=255, help_text='Name of the workspace')
    user = models.ManyToManyField(User, help_text='Reference to users table')
    fyle_org_id = models.CharField(max_length=255, help_text='org id', unique=True)
    ns_account_id = models.CharField(max_length=255, help_text='NetSuite account id')
    last_synced_at = models.DateTimeField(help_text='Datetime when expenses were pulled last', null=True)
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
    schedule = models.OneToOneField(Schedule, on_delete=models.PROTECT, null=True)


class WorkspaceGeneralSettings(models.Model):
    """
    Workspace General Settings
    """
    id = models.AutoField(primary_key=True, help_text='Unique Id to identify a workspace')
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    reimbursable_expenses_object = models.CharField(max_length=50, help_text='Reimbursable Expenses type')
    corporate_credit_card_expenses_object = models.CharField(max_length=50,
                                                             help_text='Non Reimbursable Expenses type', null=True)
    sync_fyle_to_netsuite_payments = models.BooleanField(default=False,
                                                         help_text='Auto Sync Payments from Fyle to Netsuite')
    sync_netsuite_to_fyle_payments = models.BooleanField(default=False,
                                                         help_text='Auto Sync Payments from NetSuite to Fyle')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
