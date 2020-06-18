"""
Mapping Models
"""
from django.db import models

from apps.workspaces.models import Workspace


class SubsidiaryMapping(models.Model):
    """
    Subsidiary Mapping
    """
    id = models.AutoField(primary_key=True)
    subsidiary_name = models.CharField(max_length=255, help_text='NetSuite Subsidiary name')
    internal_id = models.CharField(max_length=255, help_text='NetSuite Subsidiary id')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        unique_together = ('subsidiary_name', 'workspace')
        db_table = 'subsidiary_mappings'


class LocationMapping(models.Model):
    """
    Location Mapping
    """
    id = models.AutoField(primary_key=True)
    location_name = models.CharField(max_length=255, help_text='NetSuite Location name')
    internal_id = models.CharField(max_length=255, help_text='NetSuite Location id')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        unique_together = ('location_name', 'workspace')
        db_table = 'location_mappings'
