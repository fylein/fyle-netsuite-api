"""
NetSuite models
"""
from datetime import datetime

from django.db import models

from fyle_accounting_mappings.models import Mapping, MappingSetting

from apps.fyle.models import ExpenseGroup, Expense
from apps.mappings.models import GeneralMapping, SubsidiaryMapping


def get_department_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    department_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='DEPARTMENT'
    ).first()

    department_id = None

    if department_setting:
        source_value = None

        if lineitem:
            if department_setting.source_field == 'PROJECT':
                source_value = lineitem.project
            elif department_setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
        else:
            source_value = expense_group.description[department_setting.source_field.lower()]

        mapping: Mapping = Mapping.objects.filter(
            source_type=department_setting.source_field,
            destination_type='DEPARTMENT',
            source__value=source_value,
            workspace_id=expense_group.workspace_id
        ).first()

        if mapping:
            department_id = mapping.destination.destination_id
    return department_id


def get_class_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    class_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='CLASS'
    ).first()

    class_id = None

    if class_setting:
        source_value = None

        if lineitem:
            if class_setting.source_field == 'PROJECT':
                source_value = lineitem.project
            elif class_setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
        else:
            source_value = expense_group.description[class_setting.source_field.lower()]

        mapping: Mapping = Mapping.objects.filter(
            source_type=class_setting.source_field,
            destination_type='CLASS',
            source__value=source_value,
            workspace_id=expense_group.workspace_id
        ).first()

        if mapping:
            class_id = mapping.destination.destination_id
    return class_id


class Bill(models.Model):
    """
    NetSuite Vendor Bill
    """
    id = models.AutoField(primary_key=True)
    expense_group = models.OneToOneField(ExpenseGroup, on_delete=models.PROTECT, help_text='Expense group reference')
    accounts_payable_id = models.CharField(max_length=255, help_text='NetSuite Accounts Payable Account id')
    vendor_id = models.CharField(max_length=255, help_text='NetSuite vendor id')
    subsidiary_id = models.CharField(max_length=255, help_text='NetSuite subsidiary id')
    location_id = models.CharField(max_length=255, help_text='NetSuite Location id', null=True)
    currency = models.CharField(max_length=255, help_text='Bill Currency')
    memo = models.TextField(help_text='Bill Description')
    external_id = models.CharField(max_length=255, unique=True, help_text='Fyle reimbursement id')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'bills'

    @staticmethod
    def create_bill(expense_group: ExpenseGroup):
        """
        Create Vendor bill
        :param expense_group: expense group
        :return: vendor bill object
        """
        description = expense_group.description

        expense = expense_group.expenses.first()

        general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
        subsidiary_mappings = SubsidiaryMapping.objects.get(workspace_id=expense_group.workspace_id)

        bill_object, _ = Bill.objects.update_or_create(
            expense_group=expense_group,
            defaults={
                'subsidiary_id': subsidiary_mappings.internal_id,
                'accounts_payable_id': general_mappings.accounts_payable_id,
                'vendor_id': Mapping.objects.get(
                    source_type='EMPLOYEE',
                    destination_type='VENDOR',
                    source__value=description.get('employee_email'),
                    workspace_id=expense_group.workspace_id
                ).destination.destination_id,
                'location_id': general_mappings.location_id,
                'memo': 'Report {0} / {1} exported on {2}'.format(
                    expense.claim_number, expense.report_id, datetime.now().strftime("%Y-%m-%d")
                ),
                'currency': expense.currency,
                'external_id': expense_group.fyle_group_id
            }
        )
        return bill_object


class BillLineitem(models.Model):
    """
    NetSuite Bill Lineitem
    """
    id = models.AutoField(primary_key=True)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, help_text='Reference to bill')
    expense = models.OneToOneField(Expense, on_delete=models.PROTECT, help_text='Reference to Expense')
    account_id = models.CharField(max_length=255, help_text='NetSuite account id')
    location_id = models.CharField(max_length=255, help_text='NetSuite location id', null=True)
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    amount = models.FloatField(help_text='Bill amount')
    memo = models.CharField(max_length=255, help_text='NetSuite bill lineitem memo', null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'bill_lineitems'

    @staticmethod
    def create_bill_lineitems(expense_group: ExpenseGroup):
        """
        Create bill lineitems
        :param expense_group: expense group
        :return: lineitems objects
        """
        expenses = expense_group.expenses.all()
        bill = Bill.objects.get(expense_group=expense_group)

        bill_lineitem_objects = []

        for lineitem in expenses:
            category = lineitem.category if lineitem.category == lineitem.sub_category else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

            account: Mapping = Mapping.objects.filter(
                source_type='CATEGORY',
                destination_type='ACCOUNT',
                source__value=category,
                workspace_id=expense_group.workspace_id
            ).first()

            general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)

            class_id = get_class_id_or_none(expense_group, lineitem)

            department_id = get_department_id_or_none(expense_group, lineitem)

            bill_lineitem_object, _ = BillLineitem.objects.update_or_create(
                bill=bill,
                expense_id=lineitem.id,
                defaults={
                    'account_id': account.destination.destination_id if account else None,
                    'location_id': general_mappings.location_id,
                    'class_id': class_id,
                    'department_id': department_id,
                    'amount': lineitem.amount,
                    'memo': lineitem.purpose
                }
            )

            bill_lineitem_objects.append(bill_lineitem_object)

        return bill_lineitem_objects
