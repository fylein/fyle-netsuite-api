"""
Mapping Models
"""
from django.db import models

from apps.workspaces.models import Workspace


class EmployeeMapping(models.Model):
    """
    Employee Mappings
    """
    id = models.AutoField(primary_key=True)
    employee_email = models.CharField(max_length=255, help_text='Fyle employee email')
    vendor_name = models.CharField(max_length=255, help_text='NetSuite vendor name')
    vendor_id = models.CharField(max_length=255, help_text='NetSuite vendor id')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        unique_together = ('employee_email', 'workspace')


class CategoryMapping(models.Model):
    """
    Category Mapping
    """
    id = models.AutoField(primary_key=True)
    category = models.CharField(max_length=255, help_text='Fyle category')
    sub_category = models.CharField(max_length=255, help_text='Fyle sub category')
    account_name = models.CharField(max_length=255, help_text='NetSuite account name')
    account_id = models.CharField(max_length=255, help_text='NetSuite account id')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        unique_together = ('category', 'sub_category', 'workspace')


class ProjectMapping(models.Model):
    """
    Project Mapping
    """
    id = models.AutoField(primary_key=True)
    project = models.CharField(max_length=255, help_text='Fyle project')
    department_name = models.CharField(max_length=255, help_text='NetSuite department name')
    department_id = models.CharField(max_length=255, help_text='NetSuite department id')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        unique_together = ('project', 'workspace')


class CostCenterMapping(models.Model):
    """
    Cost Center Mapping
    """
    id = models.AutoField(primary_key=True)
    cost_center = models.CharField(max_length=255, help_text='Fyle cost center')
    location_name = models.CharField(max_length=255, help_text='NetSuite location name')
    location_id = models.CharField(max_length=255, help_text='NetSuite location id')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        unique_together = ('cost_center', 'workspace')
