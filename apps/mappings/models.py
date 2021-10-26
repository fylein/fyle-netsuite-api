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
    country_name = models.CharField(max_length=255, help_text='Netsuite Subsidiary Country', null=True)
    internal_id = models.CharField(max_length=255, help_text='NetSuite Subsidiary id')
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        db_table = 'subsidiary_mappings'


class GeneralMapping(models.Model):
    """
    General Mapping
    """
    id = models.AutoField(primary_key=True)
    location_name = models.CharField(max_length=255, help_text='NetSuite Location name', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite Location id', null=True)
    location_level = models.CharField(max_length=255, help_text='Transaction Body, Line, Both', null=True)
    accounts_payable_name = models.CharField(max_length=255, help_text='NetSuite Accounts Payable Account name',
                                             null=True)
    accounts_payable_id = models.CharField(max_length=255, help_text='NetSuite Accounts Payable Account id', null=True)
    reimbursable_account_name = models.CharField(max_length=255, help_text='Reimbursable Expenses Account name',
                                                 null=True)
    reimbursable_account_id = models.CharField(max_length=255, help_text='Reimbursable Expenses Account id', null=True)
    default_ccc_account_name = models.CharField(max_length=255, help_text='CCC Expenses Account name', null=True)
    default_ccc_account_id = models.CharField(max_length=255, help_text='CCC Expenses Account id', null=True)
    vendor_payment_account_id = models.CharField(max_length=255, help_text='NetSuite VendorPayment Account id',
                                                 null=True)
    use_employee_department = models.BooleanField(default=False, help_text='use employee department in netsuite')
    use_employee_class = models.BooleanField(default=False, help_text='use employee class in netsuite')
    use_employee_location = models.BooleanField(default=False, help_text='use employee location in netsuite')
    department_level = models.CharField(max_length=255, help_text='Transaction Body, Line, Both', null=True)
    vendor_payment_account_name = models.CharField(max_length=255, help_text='VendorPayment Account name', null=True)
    default_ccc_vendor_id = models.CharField(max_length=255, help_text='Default CCC Vendor ID', null=True)
    default_ccc_vendor_name = models.CharField(max_length=255, help_text='Default CCC Vendor Name', null=True)
    workspace = models.OneToOneField(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime')

    class Meta:
        db_table = 'general_mappings'
