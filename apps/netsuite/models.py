"""
NetSuite models
"""
from datetime import datetime

from fyle_accounting_mappings.models import Mapping, MappingSetting

from apps.fyle.models import ExpenseGroup, Expense


def get_location_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    class_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='LOCATION'
    ).first()

    class_id = None

    if class_setting:
        source_value = None

        if class_setting.source_field == 'PROJECT':
            source_value = lineitem.project
        elif class_setting.source_field == 'COST_CENTER':
            source_value = lineitem.cost_center

        mapping: Mapping = Mapping.objects.filter(
            source_type=class_setting.source_field,
            destination_type='LOCATION',
            source__value=source_value,
            workspace_id=expense_group.workspace_id
        ).first()

        if mapping:
            class_id = mapping.destination.destination_id
    return class_id


def get_department_id_or_none(expense_group: ExpenseGroup, lineitem: Expense = None):
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


# class VendorBill(models.Model):
#     """
#     NetSuite Vendor Bill
#     """
#     id = models.AutoField(primary_key=True)
#     expense_group = models.OneToOneField(ExpenseGroup, on_delete=models.PROTECT, help_text='Expense group reference')
#     accounts_payable_id = models.CharField(max_length=255, help_text='QBO Accounts Payable account id')
#     vendor_id = models.CharField(max_length=255, help_text='QBO vendor id')
#     department_id = models.CharField(max_length=255, help_text='QBO department id', null=True)
#     transaction_date = models.DateField(help_text='Bill transaction date')
#     currency = models.CharField(max_length=255, help_text='Bill Currency')
#     private_note = models.TextField(help_text='Bill Description')
#     bill_number = models.CharField(max_length=255, unique=True)
#     created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
#     updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
#
#     @staticmethod
#     def create_bill(expense_group: ExpenseGroup):
#         """
#         Create Vendor bill
#         :param expense_group: expense group
#         :return: vendor bill object
#         """
#         description = expense_group.description
#
#         expense = expense_group.expenses.first()
#
#         department_id = get_department_id_or_none(expense_group)
#
#         bill_object, _ = VendorBill.objects.update_or_create(
#             expense_group=expense_group,
#             defaults={
#                 'vendor_id': Mapping.objects.get(
#                     source_type='EMPLOYEE',
#                     destination_type='VENDOR',
#                     source__value=description.get('employee_email'),
#                     workspace_id=expense_group.workspace_id
#                 ).destination.destination_id,
#                 'department_id': department_id,
#                 'transaction_date': datetime.now().strftime("%Y-%m-%d"),
#                 'private_note': 'Report {0} / {1} exported on {2}'.format(
#                     expense.claim_number, expense.report_id, datetime.now().strftime("%Y-%m-%d")
#                 ),
#                 'bill_number': expense_group.fyle_group_id
#             }
#         )
#         return bill_object
#
#
# class BillLineitem(models.Model):
#     """
#     QBO Bill Lineitem
#     """
#     id = models.AutoField(primary_key=True)
#     bill = models.ForeignKey(VendorBill, on_delete=models.PROTECT, help_text='Reference to bill')
#     expense = models.OneToOneField(Expense, on_delete=models.PROTECT, help_text='Reference to Expense')
#     account_id = models.CharField(max_length=255, help_text='QBO account id')
#     class_id = models.CharField(max_length=255, help_text='QBO class id', null=True)
#     customer_id = models.CharField(max_length=255, help_text='QBO customer id', null=True)
#     amount = models.FloatField(help_text='Bill amount')
#     description = models.CharField(max_length=255, help_text='QBO bill lineitem description', null=True)
#     created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
#     updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
#
#     @staticmethod
#     def create_bill_lineitems(expense_group: ExpenseGroup):
#         """
#         Create bill lineitems
#         :param expense_group: expense group
#         :return: lineitems objects
#         """
#         expenses = expense_group.expenses.all()
#         bill = VendorBill.objects.get(expense_group=expense_group)
#
#         bill_lineitem_objects = []
#
#         for lineitem in expenses:
#             category = lineitem.category if lineitem.category == lineitem.sub_category else '{0} / {1}'.format(
#                 lineitem.category, lineitem.sub_category)
#
#             account: Mapping = Mapping.objects.filter(
#                 source_type='CATEGORY',
#                 destination_type='ACCOUNT',
#                 source__value=category,
#                 workspace_id=expense_group.workspace_id
#             ).first()
#
#             class_id = get_class_id_or_none(expense_group, lineitem)
#
#             customer_id = get_customer_id_or_none(expense_group, lineitem)
#
#             bill_lineitem_object, _ = BillLineitem.objects.update_or_create(
#                 bill=bill,
#                 expense_id=lineitem.id,
#                 defaults={
#                     'account_id': account.destination.destination_id if account else None,
#                     'class_id': class_id,
#                     'customer_id': customer_id,
#                     'amount': lineitem.amount,
#                     'description': lineitem.purpose
#                 }
#             )
#
#             bill_lineitem_objects.append(bill_lineitem_object)
#
#         return bill_lineitem_objects
