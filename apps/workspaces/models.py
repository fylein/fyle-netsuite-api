"""
Workspace Models
"""
from django.db import models
from django.contrib.auth import get_user_model

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


class FyleCredential(models.Model):
    """
    Table to store Fyle credentials
    """
    id = models.AutoField(primary_key=True)
    refresh_token = models.TextField(help_text='Stores Fyle refresh token')
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')
