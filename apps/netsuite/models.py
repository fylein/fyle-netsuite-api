"""
NetSuite models
"""
from datetime import datetime

from django.db import models
from django.db.models import JSONField

from fyle_accounting_mappings.models import Mapping, MappingSetting, DestinationAttribute, CategoryMapping,\
    EmployeeMapping

from apps.fyle.models import ExpenseGroup, Expense, ExpenseAttribute, ExpenseGroupSettings
from apps.mappings.models import GeneralMapping, SubsidiaryMapping
from apps.workspaces.models import Workspace, Configuration


CUSTOM_SEGMENT_CHOICES = (
    ('CUSTOM_RECORD', 'CUSTOM_RECORD'),
    ('CUSTOM_LIST', 'CUSTOM_LIST'),
    ('CUSTOM_SEGMENT', 'CUSTOM_SEGMENT')
)

def get_filtered_mapping(
    source_field: str, destination_type: str, workspace_id: int, source_value: str, source_id: str) -> Mapping:
    filters = {
        'source_type': source_field,
        'destination_type': destination_type,
        'workspace_id': workspace_id
    }

    if source_id:
        filters['source__source_id'] = source_id
    else:
        filters['source__value'] = source_value

    return Mapping.objects.filter(**filters).first()


def get_department_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    department_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='DEPARTMENT'
    ).first()

    department_id = None
    source_id = None
    source_value = None

    if department_setting:
        if lineitem:
            if department_setting.source_field == 'PROJECT':
                source_id = lineitem.project_id
                source_value = lineitem.project
            elif department_setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
            else:
                attribute = ExpenseAttribute.objects.filter(attribute_type=department_setting.source_field, workspace_id=expense_group.workspace_id).first()
                if attribute:
                    source_value = lineitem.custom_properties.get(attribute.display_name, None)

        mapping: Mapping = get_filtered_mapping(
            department_setting.source_field, 'DEPARTMENT', expense_group.workspace_id, source_value, source_id
        )

        if mapping:
            department_id = mapping.destination.destination_id
    return department_id


def get_class_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    class_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='CLASS'
    ).first()

    class_id = None
    source_id = None
    source_value = None

    if class_setting:
        if lineitem:
            if class_setting.source_field == 'PROJECT':
                source_value = lineitem.project
                source_id = lineitem.project_id
            elif class_setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
            else:
                attribute = ExpenseAttribute.objects.filter(attribute_type=class_setting.source_field, workspace_id=expense_group.workspace_id).first()
                if attribute:
                    source_value = lineitem.custom_properties.get(attribute.display_name, None)
        else:
            source_value = expense_group.description[class_setting.source_field.lower()]

        mapping: Mapping = get_filtered_mapping(
            class_setting.source_field, 'CLASS', expense_group.workspace_id, source_value, source_id
        )

        if mapping:
            class_id = mapping.destination.destination_id
    return class_id


def get_tax_group_mapping(lineitem: Expense = None, workspace_id: int = None):
    mapping: Mapping = Mapping.objects.filter(
        source_type='TAX_GROUP',
        destination_type='TAX_ITEM',
        source__source_id=lineitem.tax_group_id,
        workspace_id=workspace_id
    ).first()

    return mapping


def get_tax_item_id_or_none(expense_group: ExpenseGroup, general_mapping: GeneralMapping, lineitem: Expense = None):
    tax_code = None
    tax_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='TAX_ITEM'
    ).first()
    
    if tax_setting:
        mapping = get_tax_group_mapping(lineitem, expense_group.workspace_id)

        if mapping:
            tax_code = mapping.destination.destination_id
        else:
            tax_code = general_mapping.default_tax_code_id

    return tax_code


def get_tax_info(lineitem: Expense = None):
    tax_code, tax_rate, tax_type = None, None, None
    mapping = get_tax_group_mapping(lineitem, lineitem.workspace_id)

    if mapping:
        tax_code = mapping.destination.destination_id
        tax_rate = mapping.destination.detail.get('tax_rate')
        tax_type = mapping.destination.detail.get('tax_type_internal_id')

    return tax_code, tax_rate, tax_type


def get_customer_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    project_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='PROJECT'
    ).first()

    customer_id = None
    source_value = None
    source_id = None

    if project_setting:
        if lineitem and project_setting.source_field == 'PROJECT':
            source_value = lineitem.project
            source_id = lineitem.project_id

        mapping: Mapping = get_filtered_mapping(
            project_setting.source_field, 'PROJECT', expense_group.workspace_id, source_value, source_id
        )

        if mapping:
            customer_id = mapping.destination.destination_id
    return customer_id


def get_location_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    location_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='LOCATION'
    ).first()

    location_id = None
    source_id = None
    source_value = None

    if location_setting:
        if lineitem:
            if location_setting.source_field == 'PROJECT':
                source_value = lineitem.project
                source_id = lineitem.project_id
            elif location_setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
            else:
                attribute = ExpenseAttribute.objects.filter(attribute_type=location_setting.source_field, workspace_id=expense_group.workspace_id).first()
                if attribute:
                    source_value = lineitem.custom_properties.get(attribute.display_name, None)
        else:
            source_value = expense_group.description[location_setting.source_field.lower()]

        mapping: Mapping = get_filtered_mapping(
            location_setting.source_field, 'LOCATION', expense_group.workspace_id, source_value, source_id
        )

        if mapping:
            location_id = mapping.destination.destination_id
    return location_id


def get_custom_segments(expense_group: ExpenseGroup, lineitem: Expense):

    mapping_settings = MappingSetting.objects.filter(workspace_id=expense_group.workspace_id).all()

    custom_segments = []
    source_id = None
    source_value = None
    default_expense_attributes = ['CATEGORY', 'EMPLOYEE', 'TAX_GROUP', 'CORPORATE_CARD']
    default_destination_attributes = ['DEPARTMENT', 'CLASS', 'PROJECT', 'LOCATION']

    for setting in mapping_settings:
        if setting.source_field not in default_expense_attributes and \
                setting.destination_field not in default_destination_attributes:
            if setting.source_field == 'PROJECT':
                source_value = lineitem.project
                source_id = lineitem.project_id
            elif setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
            else:
                attribute = ExpenseAttribute.objects.filter(
                    attribute_type=setting.source_field,
                    workspace_id=expense_group.workspace_id
                ).first()
                if attribute:
                    source_value = lineitem.custom_properties.get(attribute.display_name, None)

            mapping: Mapping = get_filtered_mapping(
               setting.source_field, setting.destination_field, expense_group.workspace_id, source_value, source_id
            )

            if mapping:
                # trim -CS from custom segment name
                name = setting.destination_field.split('-')[0] if '-CS' in setting.destination_field else setting.destination_field
                cus_list = CustomSegment.objects.filter(
                    name=name,
                    workspace_id=expense_group.workspace_id
                ).first()
                value = mapping.destination.destination_id
                custom_segments.append({
                    'scriptId': cus_list.script_id,
                    'type': 'Select',
                    'value': value
                })

    return custom_segments


def get_transaction_date(expense_group: ExpenseGroup) -> str:
    if 'spent_at' in expense_group.description and expense_group.description['spent_at']:
        return expense_group.description['spent_at']
    elif 'approved_at' in expense_group.description and expense_group.description['approved_at']:
        return expense_group.description['approved_at']
    elif 'verified_at' in expense_group.description and expense_group.description['verified_at']:
        return expense_group.description['verified_at']
    elif 'posted_at' in expense_group.description and expense_group.description['posted_at']:
        return expense_group.description['posted_at']
    elif 'last_spent_at' in expense_group.description and expense_group.description['last_spent_at']:
        return expense_group.description['last_spent_at']

    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


def get_expense_purpose(lineitem, category, configuration) -> str:
    memo_structure = configuration.memo_structure

    details = {
        'employee_email': lineitem.employee_email,
        'employee_name': lineitem.employee_name,
        'card_number': '{0}'.format(lineitem.masked_corporate_card_number) if lineitem.masked_corporate_card_number else '',
        'merchant': '{0}'.format(lineitem.vendor) if lineitem.vendor else '',
        'category': '{0}'.format(category) if lineitem.category else '',
        'purpose': '{0}'.format(lineitem.purpose) if lineitem.purpose else '',
        'report_number': '{0}'.format(lineitem.claim_number),
        'spent_on': '{0}'.format(lineitem.spent_at.date()) if lineitem.spent_at else ''
    }

    purpose = ''

    for id, field in enumerate(memo_structure):
        if field in details:
            purpose += details[field]
            if id + 1 != len(memo_structure):
                if details[field]:
                    purpose = '{0} - '.format(purpose)

    purpose = purpose.replace('<', '')
    purpose = purpose.replace('>', '')

    return purpose

def get_ccc_account_id(configuration: Configuration, general_mappings: GeneralMapping, expense: Expense, description: str):
    if configuration.map_fyle_cards_netsuite_account:
        ccc_account = Mapping.objects.filter(
            source_type='CORPORATE_CARD',
            destination_type='CREDIT_CARD_ACCOUNT',
            source__source_id=expense.corporate_card_id,
            workspace_id=configuration.workspace_id
        ).first()

        if ccc_account:
            ccc_account_id = ccc_account.destination.destination_id
        else:
            ccc_account_id = general_mappings.default_ccc_account_id
    else:
        ccc_account_mapping: EmployeeMapping = EmployeeMapping.objects.filter(
            source_employee__value=description.get('employee_email'),
            workspace_id=configuration.workspace_id
        ).first()
        ccc_account_id = ccc_account_mapping.destination_card_account.destination_id \
            if ccc_account_mapping and ccc_account_mapping.destination_card_account \
            else general_mappings.default_ccc_account_id

    return ccc_account_id

def get_report_or_expense_number(expense_group: ExpenseGroup) -> str:       
        expense: Expense = expense_group.expenses.first()
        expense_group_settings: ExpenseGroupSettings = ExpenseGroupSettings.objects.get(workspace_id= expense_group.workspace_id)
        if expense_group.fund_source == 'CCC':
                return expense.expense_number
        else:
            if 'expense_id' in expense_group_settings.reimbursable_expense_group_fields:
                return expense.expense_number 
            else:
                return expense.claim_number
            
def get_category_mapping_and_detail_type(configuration: Configuration, category: str, workspace_id: int):
    # get the item-mapping if import_items is true
    if configuration.import_items:
        netsuite_item = CategoryMapping.objects.filter(
            destination_account__display_name = 'Item',
            source_category__value=category,
            workspace_id=workspace_id
        ).first()
        if netsuite_item:
            return netsuite_item, 'ItemBasedExpenseLineDetail'

    # else get the account-mapping
    netsuite_account = CategoryMapping.objects.filter(
        destination_account__display_name = 'Account',
        source_category__value=category,
        workspace_id=workspace_id
    ).first()

    return netsuite_account, 'AccountBasedExpenseLineDetail'

class CustomSegment(models.Model):
    """
    NetSuite Custom Segment
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, help_text='NetSuite Record Name')
    segment_type = models.CharField(max_length=255, choices=CUSTOM_SEGMENT_CHOICES, help_text='NetSuite Custom Type')
    script_id = models.CharField(max_length=255, help_text='NetSuite Transaction Custom Field script id')
    internal_id = models.CharField(max_length=255, help_text='NetSuite Custom Record / Field internal id')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        unique_together = ('script_id', 'internal_id', 'workspace')
        db_table = 'custom_segments'


class Bill(models.Model):
    """
    NetSuite Vendor Bill
    """
    id = models.AutoField(primary_key=True)
    expense_group = models.OneToOneField(ExpenseGroup, on_delete=models.PROTECT, help_text='Expense group reference')
    accounts_payable_id = models.CharField(max_length=255, help_text='NetSuite Accounts Payable Account id')
    entity_id = models.CharField(max_length=255, help_text='NetSuite vendor id')
    subsidiary_id = models.CharField(max_length=255, help_text='NetSuite subsidiary id')
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite Location id', null=True)
    currency = models.CharField(max_length=255, help_text='Bill Currency')
    memo = models.TextField(help_text='Bill Description')
    override_tax_details = models.BooleanField(help_text='Override Tax Details', default=False)
    reference_number = models.CharField(max_length=255, help_text='NetSuite reference number', null=True)
    external_id = models.CharField(max_length=255, unique=True, help_text='Fyle reimbursement id')
    transaction_date = models.DateTimeField(help_text='Bill transaction date')
    payment_synced = models.BooleanField(help_text='Payment synced status', default=False)
    paid_on_netsuite = models.BooleanField(help_text='Payment Status in NetSuite', default=False)
    is_retired = models.BooleanField(help_text='Is Payment sync retried', default=False)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
    is_attachment_upload_failed = models.BooleanField(help_text='Is Attachment Upload Failed', default=False)

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

        currency = DestinationAttribute.objects.filter(value=expense.currency,
                                                       workspace_id=expense_group.workspace_id,
                                                       attribute_type='CURRENCY').first()
        vendor_id = None
        if expense_group.fund_source == 'PERSONAL':
            vendor_id = EmployeeMapping.objects.get(
                source_employee__value=description.get('employee_email'),
                workspace_id=expense_group.workspace_id
            ).destination_vendor.destination_id
        elif expense_group.fund_source == 'CCC':
            vendor_id = general_mappings.default_ccc_vendor_id

        bill_object, _ = Bill.objects.update_or_create(
            expense_group=expense_group,
            defaults={
                'subsidiary_id': subsidiary_mappings.internal_id,
                'accounts_payable_id': general_mappings.accounts_payable_id,
                'entity_id': vendor_id,
                'department_id': general_mappings.department_id if general_mappings.department_level in [
                    'TRANSACTION_BODY', 'ALL'] else None,
                'class_id': general_mappings.class_id if general_mappings.class_level in [
                    'TRANSACTION_BODY', 'ALL'] else None,
                'location_id': general_mappings.location_id if general_mappings.location_level in [
                    'TRANSACTION_BODY', 'ALL'] else None,
                'memo': 'Reimbursable expenses by {0}'.format(description.get('employee_email')) if
                expense_group.fund_source == 'PERSONAL' else
                'Credit card expenses by {0}'.format(description.get('employee_email')),
                'reference_number': get_report_or_expense_number(expense_group),
                'currency': currency.destination_id if currency else '1',
                'override_tax_details': general_mappings.override_tax_details,
                'transaction_date': get_transaction_date(expense_group),
                'external_id': 'bill {} - {}'.format(expense_group.id, description.get('employee_email'))
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
    account_id = models.CharField(max_length=255, help_text='NetSuite account id', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite location id', null=True)
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    customer_id = models.CharField(max_length=255, help_text='NetSuite customer id', null=True)
    amount = models.FloatField(help_text='Bill amount')
    tax_amount = models.FloatField(null=True, help_text='Tax amount')
    tax_item_id = models.CharField(max_length=255, help_text='Tax Item ID', null=True)
    billable = models.BooleanField(null=True, help_text='Expense Billable or not')
    memo = models.TextField(help_text='NetSuite bill lineitem memo', null=True)
    netsuite_custom_segments = JSONField(null=True, help_text='NetSuite Custom Segments')
    netsuite_receipt_url = models.TextField(null=True, help_text='NetSuite Receipt URL')
    item_id = models.CharField(max_length=255, help_text='Netsuite item id', null=True)
    detail_type = models.CharField(max_length=255, help_text='Detail type for the lineitem', default='AccountBasedExpenseLineDetail')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'bill_lineitems'

    @staticmethod
    def create_bill_lineitems(expense_group: ExpenseGroup, configuration: Configuration):
        """
        Create bill lineitems
        :param expense_group: expense group
        :param configuration: Workspace Configuration Settings
        :return: lineitems objects
        """
        expenses = expense_group.expenses.all()
        bill = Bill.objects.get(expense_group=expense_group)
        general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)

        bill_lineitem_objects = []

        for lineitem in expenses:
            category = lineitem.category if (lineitem.category == lineitem.sub_category or lineitem.sub_category == None) else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

            account, detail_type = get_category_mapping_and_detail_type(configuration, category, configuration.workspace_id)

            class_id = get_class_id_or_none(expense_group, lineitem)
            if not class_id and expense_group.fund_source == 'CCC' and general_mappings.use_employee_class:
                employee_mapping = EmployeeMapping.objects.filter(
                    source_employee__value=expense_group.description.get('employee_email'),
                    workspace_id=expense_group.workspace_id
                ).first()
                if employee_mapping and employee_mapping.destination_employee:
                    class_id = employee_mapping.destination_employee.detail.get('class_id')

            department_id = get_department_id_or_none(expense_group, lineitem)

            if not department_id and expense_group.fund_source == 'CCC' and general_mappings.use_employee_department and \
                general_mappings.department_level in ('ALL', 'TRANSACTION_LINE'):
                employee_mapping = EmployeeMapping.objects.filter(
                    source_employee__value=expense_group.description.get('employee_email'),
                    workspace_id=expense_group.workspace_id
                ).first()
                if employee_mapping and employee_mapping.destination_employee:
                    if employee_mapping.destination_employee.detail.get('department_id'):
                        department_id = employee_mapping.destination_employee.detail.get('department_id')
            
            if not department_id:
                if general_mappings.department_id and general_mappings.department_level in ['TRANSACTION_LINE', 'ALL']:
                    department_id = general_mappings.department_id

            location_id = get_location_id_or_none(expense_group, lineitem)

            if not location_id and expense_group.fund_source == 'CCC' and general_mappings.use_employee_location and\
                    general_mappings.location_level in ('ALL', 'TRANSACTION_LINE'):
                employee_mapping = EmployeeMapping.objects.filter(
                    source_employee__value=expense_group.description.get('employee_email'),
                    workspace_id=expense_group.workspace_id
                ).first()
                if employee_mapping and employee_mapping.destination_employee:
                    location_id = employee_mapping.destination_employee.detail.get('location_id')

            if not location_id and general_mappings.location_id and \
                general_mappings.location_level in ['TRANSACTION_LINE', 'ALL']:
                location_id = general_mappings.location_id

            custom_segments = get_custom_segments(expense_group, lineitem)

            customer_id = get_customer_id_or_none(expense_group, lineitem)

            billable = lineitem.billable
            if customer_id:
                if not billable:
                    billable = False
            else:
                billable = None

            bill_lineitem_object, _ = BillLineitem.objects.update_or_create(
                bill=bill,
                expense_id=lineitem.id,
                defaults={
                    'account_id': account.destination_account.destination_id \
                        if account and detail_type == 'AccountBasedExpenseLineDetail' else None,
                    'item_id': account.destination_account.destination_id \
                        if account and detail_type == 'ItemBasedExpenseLineDetail' else None,
                    'detail_type': detail_type,
                    'location_id': location_id,
                    'class_id': class_id,
                    'department_id': department_id,
                    'customer_id': customer_id,
                    'amount': lineitem.amount,
                    'tax_item_id': get_tax_item_id_or_none(expense_group, general_mappings,lineitem),
                    'tax_amount': lineitem.tax_amount,
                    'billable': billable,
                    'memo': get_expense_purpose(lineitem, category, configuration),
                    'netsuite_custom_segments': custom_segments
                }
            )

            bill_lineitem_objects.append(bill_lineitem_object)

        return bill_lineitem_objects


class CreditCardCharge(models.Model):
    """
    NetSuite Credit Card Charge
    """
    id = models.AutoField(primary_key=True)
    expense_group = models.OneToOneField(ExpenseGroup, on_delete=models.PROTECT, help_text='Expense group reference')
    credit_card_account_id = models.CharField(max_length=255, help_text='NetSuite Accounts Payable Account id')
    entity_id = models.CharField(max_length=255, help_text='NetSuite vendor id')
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    subsidiary_id = models.CharField(max_length=255, help_text='NetSuite subsidiary id')
    location_id = models.CharField(max_length=255, help_text='NetSuite Location id', null=True)
    currency = models.CharField(max_length=255, help_text='CC Charge Currency')
    memo = models.TextField(help_text='CC Charge Description')
    reference_number = models.CharField(max_length=255, help_text='NetSuite reference number', null=True)
    external_id = models.CharField(max_length=255, unique=True, help_text='Fyle reimbursement id')
    transaction_date = models.DateTimeField(help_text='CC Charge transaction date')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
    is_attachment_upload_failed = models.BooleanField(help_text='Is Attachment Upload Failed', default=False)

    class Meta:
        db_table = 'credit_card_charges'

    @staticmethod
    def create_credit_card_charge(expense_group: ExpenseGroup):
        """
        Create Credit Card Charge
        :param expense_group: expense group
        :return: charge card tranasaction object
        """
        description = expense_group.description

        expense = expense_group.expenses.first()

        general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
        subsidiary_mappings = SubsidiaryMapping.objects.get(workspace_id=expense_group.workspace_id)
        configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)
        employee_field_mapping = configuration.employee_field_mapping

        ccc_account_id = get_ccc_account_id(configuration, general_mappings, expense, description)

        currency = DestinationAttribute.objects.filter(value=expense.currency,
                                                       workspace_id=expense_group.workspace_id,
                                                       attribute_type='CURRENCY').first()

        merchant = expense.vendor if expense.vendor else ''

        vendor = DestinationAttribute.objects.filter(
            value__iexact=merchant, attribute_type='VENDOR', workspace_id=expense_group.workspace_id
        ).order_by('-updated_at').first()

        if not vendor:
            vendor_id = general_mappings.default_ccc_vendor_id
        else:
            vendor_id = vendor.destination_id
            
        department_id = None
        employee_mapping = EmployeeMapping.objects.filter(
            source_employee__value=description.get('employee_email'),
            workspace_id=expense_group.workspace_id
        ).first()

        if general_mappings.use_employee_department and general_mappings.department_level in (
            'ALL', 'TRANSACTION_BODY') and employee_field_mapping == 'EMPLOYEE' and employee_mapping \
            and employee_mapping.destination_employee and employee_mapping.destination_employee.detail:
            department_id = employee_mapping.destination_employee.detail.get('department_id')

        credit_charge_object, _ = CreditCardCharge.objects.update_or_create(
            expense_group=expense_group,
            defaults={
                'subsidiary_id': subsidiary_mappings.internal_id,
                'credit_card_account_id': ccc_account_id,
                'department_id': department_id,
                'class_id': general_mappings.class_id if general_mappings.class_level in [
                    'TRANSACTION_BODY', 'ALL'] else None,
                'entity_id': vendor_id,
                'location_id': general_mappings.location_id if general_mappings.location_level in [
                    'TRANSACTION_BODY', 'ALL'] else None,
                'memo': 'Credit card expenses by {0}'.format(description.get('employee_email')),
                'reference_number': get_report_or_expense_number(expense_group),
                'currency': currency.destination_id if currency else '1',
                'transaction_date': get_transaction_date(expense_group).partition('T')[0],
                'external_id': 'cc-charge {} - {}'.format(expense_group.id, description.get('employee_email'))
            }
        )
        return credit_charge_object


class CreditCardChargeLineItem(models.Model):
    """
    NetSuite Credit Card Charge Lineitem
    """
    id = models.AutoField(primary_key=True)
    credit_card_charge = models.ForeignKey(
        CreditCardCharge, on_delete=models.PROTECT, help_text='Reference to credit card charge')
    expense = models.OneToOneField(Expense, on_delete=models.PROTECT, help_text='Reference to Expense')
    account_id = models.CharField(max_length=255, help_text='NetSuite account id')
    location_id = models.CharField(max_length=255, help_text='NetSuite location id', null=True)
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    customer_id = models.CharField(max_length=255, help_text='NetSuite customer id', null=True)
    amount = models.FloatField(help_text='CC Charge line amount')
    tax_amount = models.FloatField(null=True, help_text='Tax amount')
    tax_item_id = models.CharField(max_length=255, help_text='Tax Item ID', null=True)
    billable = models.BooleanField(null=True, help_text='Expense Billable or not')
    memo = models.TextField(help_text='NetSuite cc charge lineitem memo', null=True)
    netsuite_custom_segments = JSONField(null=True, help_text='NetSuite Custom Segments')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
    netsuite_receipt_url = models.TextField(null=True, help_text='NetSuite Receipt URL')

    class Meta:
        db_table = 'credit_card_charge_lineitems'

    @staticmethod
    def create_credit_card_charge_lineitems(expense_group: ExpenseGroup, configuration: Configuration):
        """
        Create credit card charge lineitems
        :param expense_group: expense group
        :param configuration: Workspace Configuration Settings
        :return: credit card charge lineitems objects
        """
        credit_card_charge = CreditCardCharge.objects.get(expense_group=expense_group)
        general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)

        credit_card_charge_lineitem_objects = []
        for lineitem in expense_group.expenses.all():

            category = lineitem.category if (lineitem.category == lineitem.sub_category or lineitem.sub_category == None) else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

            account = CategoryMapping.objects.filter(
                source_category__value=category,
                workspace_id=expense_group.workspace_id
            ).first()

            class_id = get_class_id_or_none(expense_group, lineitem)
            if not class_id and expense_group.fund_source == 'CCC' and general_mappings.use_employee_class:
                employee_mapping = EmployeeMapping.objects.filter(
                    source_employee__value=expense_group.description.get('employee_email'),
                    workspace_id=expense_group.workspace_id
                ).first()
                if employee_mapping and employee_mapping.destination_employee:
                    class_id = employee_mapping.destination_employee.detail.get('class_id')

            department_id = get_department_id_or_none(expense_group, lineitem)

            if not department_id and expense_group.fund_source == 'CCC' and general_mappings.use_employee_department and \
                general_mappings.department_level in ('ALL', 'TRANSACTION_LINE'):
                employee_mapping = EmployeeMapping.objects.filter(
                    source_employee__value=expense_group.description.get('employee_email'),
                    workspace_id=expense_group.workspace_id
                ).first()
                if employee_mapping and employee_mapping.destination_employee:
                    if employee_mapping.destination_employee.detail.get('department_id'):
                        department_id = employee_mapping.destination_employee.detail.get('department_id')

            if not department_id:
                if general_mappings.department_id and general_mappings.department_level in ['TRANSACTION_LINE', 'ALL']:
                    department_id = general_mappings.department_id

            location_id = get_location_id_or_none(expense_group, lineitem)

            if not location_id and expense_group.fund_source == 'CCC' and general_mappings.use_employee_location and\
                        general_mappings.location_level in ('ALL', 'TRANSACTION_LINE'):
                    employee_mapping = EmployeeMapping.objects.filter(
                        source_employee__value=expense_group.description.get('employee_email'),
                        workspace_id=expense_group.workspace_id
                    ).first()
                    if employee_mapping and employee_mapping.destination_employee:
                        location_id = employee_mapping.destination_employee.detail.get('location_id')

            if not location_id:
                if general_mappings.location_id and general_mappings.location_level in ['TRANSACTION_LINE', 'ALL']:
                    location_id = general_mappings.location_id

            custom_segments = get_custom_segments(expense_group, lineitem)

            customer_id = get_customer_id_or_none(expense_group, lineitem)

            billable = lineitem.billable
            if customer_id:
                if not billable:
                    billable = False
            else:
                billable = False

            credit_card_charge_lineitem_object, _ = CreditCardChargeLineItem.objects.update_or_create(
                credit_card_charge=credit_card_charge,
                expense_id=lineitem.id,
                defaults={
                    'account_id': account.destination_account.destination_id \
                        if account and account.destination_account else None,
                    'location_id': location_id,
                    'class_id': class_id,
                    'department_id': department_id,
                    'customer_id': customer_id,
                    'amount': lineitem.amount,
                    'tax_item_id': get_tax_item_id_or_none(expense_group, general_mappings,lineitem),
                    'tax_amount': lineitem.tax_amount,
                    'billable': billable,
                    'memo': get_expense_purpose(lineitem, category, configuration),
                    'netsuite_custom_segments': custom_segments
                }
            )

            credit_card_charge_lineitem_objects.append(credit_card_charge_lineitem_object)

        return credit_card_charge_lineitem_objects


class ExpenseReport(models.Model):
    """
    NetSuite Expense Report
    """
    id = models.AutoField(primary_key=True)
    expense_group = models.OneToOneField(ExpenseGroup, on_delete=models.PROTECT, help_text='Expense group reference')
    account_id = models.CharField(max_length=255, help_text='NetSuite Account id')
    credit_card_account_id = models.CharField(max_length=255, help_text='NetSuite Credit Card Account id', null=True)
    entity_id = models.CharField(max_length=255, help_text='NetSuite Entity id (Employee / Vendor)')
    currency = models.CharField(max_length=255, help_text='Expense Report Currency')
    department_id = models.CharField(max_length=255, help_text='NetSuite Department id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite Location id', null=True)
    subsidiary_id = models.CharField(max_length=255, help_text='NetSuite subsidiary id')
    memo = models.TextField(help_text='Expense Report Description')
    external_id = models.CharField(max_length=255, unique=True, help_text='Fyle reimbursement id')
    transaction_date = models.DateTimeField(help_text='Expense Report transaction date')
    payment_synced = models.BooleanField(help_text='Payment synced status', default=False)
    paid_on_netsuite = models.BooleanField(help_text='Payment Status in NetSuite', default=False)
    is_retired = models.BooleanField(help_text='Is Payment sync retried', default=False)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
    is_attachment_upload_failed = models.BooleanField(help_text='Is Attachment Upload Failed', default=False)

    class Meta:
        db_table = 'expense_reports'

    @staticmethod
    def create_expense_report(expense_group: ExpenseGroup):
        """
        Create Expense Report
        :param expense_group: expense group
        :return: expense report object
        """
        description = expense_group.description

        expense = expense_group.expenses.first()

        general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
        subsidiary_mappings = SubsidiaryMapping.objects.get(workspace_id=expense_group.workspace_id)
        configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)

        currency = DestinationAttribute.objects.filter(value=expense.currency,
                                                       workspace_id=expense_group.workspace_id,
                                                       attribute_type='CURRENCY').first()

        debit_account_id = GeneralMapping.objects.get(
            workspace_id=expense_group.workspace_id).reimbursable_account_id

        credit_card_account_id = get_ccc_account_id(configuration, general_mappings, expense, description)

        configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)
        employee_field_mapping = configuration.employee_field_mapping

        department_id = None
        class_id = None

        employee_mapping = EmployeeMapping.objects.filter(
            source_employee__value=description.get('employee_email'),
            workspace_id=expense_group.workspace_id
        ).first()

        if general_mappings.use_employee_department and general_mappings.department_level in (
            'ALL', 'TRANSACTION_BODY') and employee_field_mapping == 'EMPLOYEE':
            department_id = employee_mapping.destination_employee.detail.get('department_id')
        else:
            department_id = general_mappings.department_id if general_mappings.department_level in [
                    'TRANSACTION_BODY', 'ALL'] else None

        if general_mappings.use_employee_location and general_mappings.location_level in ('ALL', 'TRANSACTION_BODY') \
                and employee_field_mapping == 'EMPLOYEE':
            location_id = employee_mapping.destination_employee.detail.get('location_id')
        else:
            location_id = general_mappings.location_id if general_mappings.location_level in [
                    'TRANSACTION_BODY', 'ALL'] else None

        if not class_id and general_mappings.use_employee_class and employee_field_mapping == 'EMPLOYEE':
            class_id = employee_mapping.destination_employee.detail.get('class_id')

        expense_report_object, _ = ExpenseReport.objects.update_or_create(
            expense_group=expense_group,
            defaults={
                'account_id': debit_account_id,
                'credit_card_account_id': credit_card_account_id if expense_group.fund_source == 'CCC' else None,
                'entity_id': EmployeeMapping.objects.get(
                    source_employee__value=description.get('employee_email'),
                    workspace_id=expense_group.workspace_id
                ).destination_employee.destination_id,
                'currency': currency.destination_id if currency else '1',
                'department_id': department_id,
                'class_id': class_id,
                'location_id': location_id,
                'subsidiary_id': subsidiary_mappings.internal_id,
                'memo': 'Reimbursable expenses by {0}'.format(description.get('employee_email')) if
                expense_group.fund_source == 'PERSONAL' else
                'Credit card expenses by {0}'.format(description.get('employee_email')),
                'transaction_date': get_transaction_date(expense_group),
                'external_id': 'report {} - {}'.format(expense_group.id, description.get('employee_email'))
            }
        )
        return expense_report_object


class ExpenseReportLineItem(models.Model):
    """
    NetSuite Expense Report Lineitem
    """
    id = models.AutoField(primary_key=True)
    expense_report = models.ForeignKey(ExpenseReport, on_delete=models.PROTECT, help_text='Reference to expense_report')
    expense = models.OneToOneField(Expense, on_delete=models.PROTECT, help_text='Reference to Expense')
    amount = models.FloatField(help_text='ExpenseReport amount')
    billable = models.BooleanField(null=True, help_text='Expense Billable or not')
    category = models.CharField(max_length=255, help_text='NetSuite category account id')
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    customer_id = models.CharField(max_length=255, help_text='NetSuite Customer id', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite location id', null=True)
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    currency = models.CharField(max_length=255, help_text='NetSuite Currency id')
    tax_amount = models.FloatField(null=True, help_text='Tax amount')
    tax_item_id = models.CharField(max_length=255, help_text='Tax Item ID', null=True)
    memo = models.TextField(help_text='NetSuite ExpenseReport lineitem memo', null=True)
    netsuite_custom_segments = JSONField(null=True, help_text='NetSuite Custom Segments')
    netsuite_receipt_url = models.TextField(null=True, help_text='NetSuite Receipt URL')
    transaction_date = models.DateTimeField(help_text='Expense Report transaction date')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'expense_report_lineitems'

    @staticmethod
    def create_expense_report_lineitems(expense_group: ExpenseGroup, configuration: Configuration):
        """
        Create expense report lineitems
        :param expense_group: expense group
        :param configuration: Workspace Configuration Settings
        :return: lineitems objects
        """
        expenses = expense_group.expenses.all()
        expense_report = ExpenseReport.objects.get(expense_group=expense_group)
        general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)

        configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)
        employee_field_mapping = configuration.employee_field_mapping
        description = expense_group.description

        expense_report_lineitem_objects = []

        for lineitem in expenses:
            category = lineitem.category if (lineitem.category == lineitem.sub_category or lineitem.sub_category == None) else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

            account = CategoryMapping.objects.filter(
                source_category__value=category,
                workspace_id=expense_group.workspace_id
            ).first()

            entity = EmployeeMapping.objects.get(
                source_employee__value=description.get('employee_email'),
                workspace_id=expense_group.workspace_id
            )

            currency = DestinationAttribute.objects.filter(value=lineitem.currency,
                                                           workspace_id=expense_group.workspace_id,
                                                           attribute_type='CURRENCY').first()

            class_id = get_class_id_or_none(expense_group, lineitem)
            department_id = get_department_id_or_none(expense_group, lineitem)

            if not class_id and general_mappings.use_employee_class and employee_field_mapping == 'EMPLOYEE':
                class_id = entity.destination_employee.detail.get('class_id')

            if not department_id and general_mappings.use_employee_department and \
                general_mappings.department_level in ('ALL', 'TRANSACTION_LINE') and \
                    employee_field_mapping == 'EMPLOYEE':
                if entity.destination_employee.detail.get('department_id'):
                    department_id = entity.destination_employee.detail.get('department_id')
 
            if not department_id:
                if general_mappings.department_id and general_mappings.department_level in ['TRANSACTION_LINE', 'ALL']:
                    department_id = general_mappings.department_id

            location_id = get_location_id_or_none(expense_group, lineitem)

            if not location_id and general_mappings.use_employee_location and \
                general_mappings.location_level in ('ALL', 'TRANSACTION_LINE') and \
                    employee_field_mapping == 'EMPLOYEE':
                location_id = entity.destination_employee.detail.get('location_id')     

            if not location_id:
                if general_mappings.location_id and general_mappings.location_level in ['TRANSACTION_LINE', 'ALL']:
                    location_id = general_mappings.location_id

            customer_id = get_customer_id_or_none(expense_group, lineitem)
            custom_segments = get_custom_segments(expense_group, lineitem)

            billable = lineitem.billable
            if customer_id:
                if not billable:
                    billable = False
            else:
                billable = None

            expense_report_lineitem_object, _ = ExpenseReportLineItem.objects.update_or_create(
                expense_report=expense_report,
                expense_id=lineitem.id,
                defaults={
                    'amount': lineitem.amount,
                    'billable': billable,
                    'category': account.destination_expense_head.destination_id if account and account.destination_expense_head else None,
                    'class_id': class_id if class_id else None,
                    'customer_id': customer_id,
                    'location_id': location_id,
                    'department_id': department_id,
                    'currency': currency.destination_id if currency else '1',
                    'tax_item_id': get_tax_item_id_or_none(expense_group, general_mappings,lineitem),
                    'tax_amount': lineitem.tax_amount,
                    'transaction_date': get_transaction_date(expense_group),
                    'memo': get_expense_purpose(lineitem, category, configuration),
                    'netsuite_custom_segments': custom_segments
                }
            )

            expense_report_lineitem_objects.append(expense_report_lineitem_object)

        return expense_report_lineitem_objects


class JournalEntry(models.Model):
    """
    NetSuite Journal Entry Model
    """
    id = models.AutoField(primary_key=True)
    expense_group = models.OneToOneField(ExpenseGroup, on_delete=models.PROTECT, help_text='Expense group reference')
    currency = models.CharField(max_length=255, help_text='Journal Entry Currency')
    location_id = models.CharField(max_length=255, help_text='NetSuite Location id', null=True)
    department_id = models.CharField(max_length=255, help_text='NetSuite Department id', null=True)
    subsidiary_id = models.CharField(max_length=255, help_text='NetSuite Subsidiary ID')
    memo = models.TextField(help_text='Journal Entry Memo')
    external_id = models.CharField(max_length=255, unique=True, help_text='Journal Entry External ID')
    transaction_date = models.DateTimeField(help_text='Journal Entry transaction date')
    payment_synced = models.BooleanField(help_text='Payment synced status', default=False)
    paid_on_netsuite = models.BooleanField(help_text='Payment Status in NetSuite', default=False)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
    is_attachment_upload_failed = models.BooleanField(help_text='Is Attachment Upload Failed', default=False)

    class Meta:
        db_table = 'journal_entries'

    @staticmethod
    def create_journal_entry(expense_group: ExpenseGroup):
        """
        Create JournalEntry
        :param expense_group: expense group
        :return: JournalEntry object
        """
        expense = expense_group.expenses.first()

        description = expense_group.description

        currency = DestinationAttribute.objects.filter(value=expense.currency,
                                                       workspace_id=expense_group.workspace_id,
                                                       attribute_type='CURRENCY').first()

        subsidiary_mappings = SubsidiaryMapping.objects.get(workspace_id=expense_group.workspace_id)

        general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)

        configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)
        employee_field_mapping = configuration.employee_field_mapping

        department_id = None
        location_id = None

        employee_mapping = EmployeeMapping.objects.filter(
            source_employee__value=expense_group.description.get('employee_email'),
            workspace_id=expense_group.workspace_id
        ).first()

        if general_mappings.use_employee_department and general_mappings.department_level in ('ALL', 'TRANSACTION_BODY')\
            and employee_field_mapping == 'EMPLOYEE' and employee_mapping and employee_mapping.destination_employee:
            department_id = employee_mapping.destination_employee.detail.get('department_id')

        if general_mappings.use_employee_location and general_mappings.location_level in ('ALL', 'TRANSACTION_BODY')\
            and employee_field_mapping == 'EMPLOYEE' and employee_mapping and employee_mapping.destination_employee:   
            location_id = employee_mapping.destination_employee.detail.get('location_id')

        journal_entry_object, _ = JournalEntry.objects.update_or_create(
            expense_group=expense_group,
            defaults={
                'currency': currency.destination_id if currency else '1',
                'location_id': location_id if location_id else general_mappings.location_id,
                'subsidiary_id': subsidiary_mappings.internal_id,
                'department_id': department_id,
                'memo': 'Reimbursable expenses by {0}'.format(description.get('employee_email')) if
                expense_group.fund_source == 'PERSONAL' else
                'Credit card expenses by {0}'.format(description.get('employee_email')),
                'transaction_date': get_transaction_date(expense_group),
                'external_id': 'journal {} - {}'.format(expense_group.id, description.get('employee_email'))
            }
        )
        return journal_entry_object


class JournalEntryLineItem(models.Model):
    """
    Create Journal Entry Lineitems
    """
    id = models.AutoField(primary_key=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.PROTECT, help_text='Reference to JournalEntry')
    expense = models.OneToOneField(Expense, on_delete=models.PROTECT, help_text='Reference to Expense')
    debit_account_id = models.CharField(max_length=255, help_text='NetSuite Debit account id')
    account_id = models.CharField(max_length=255, help_text='NetSuite account id')
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite location id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite class id', null=True)
    entity_id = models.CharField(max_length=255, help_text='NetSuite entity id')
    amount = models.FloatField(help_text='JournalEntry amount')
    tax_amount = models.FloatField(null=True, help_text='Tax amount')
    tax_item_id = models.CharField(max_length=255, help_text='Tax Item ID', null=True)
    memo = models.TextField(help_text='NetSuite JournalEntry lineitem description', null=True)
    netsuite_custom_segments = JSONField(null=True, help_text='NetSuite Custom Segments')
    netsuite_receipt_url = models.TextField(null=True, help_text='NetSuite Receipt URL')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'journal_entry_lineitems'

    @staticmethod
    def create_journal_entry_lineitems(expense_group: ExpenseGroup, configuration: Configuration):
        """
        Create Journal Entry Lineitems
        :param expense_group: expense group
        :param configuration: Workspace Configuration Settings
        :return: lineitem objects
        """
        expenses = expense_group.expenses.all()
        journal_entry = JournalEntry.objects.get(expense_group=expense_group)

        general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)

        description = expense_group.description

        debit_account_id = None

        configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)
        employee_field_mapping = configuration.employee_field_mapping

        journal_entry_lineitem_objects = []

        for lineitem in expenses:
            category = lineitem.category if (lineitem.category == lineitem.sub_category or lineitem.sub_category == None) else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

            entity_id = None
            employee_mapping = EmployeeMapping.objects.filter(
                source_employee__value=expense_group.description.get('employee_email'),
                workspace_id=expense_group.workspace_id
            ).first()

            if expense_group.fund_source == 'PERSONAL':
                entity_id = employee_mapping.destination_employee.destination_id if employee_field_mapping == 'EMPLOYEE' \
                    else employee_mapping.destination_vendor.destination_id
                if employee_field_mapping == 'VENDOR':
                    debit_account_id = general_mappings.accounts_payable_id
                elif employee_field_mapping == 'EMPLOYEE':
                    debit_account_id = general_mappings.reimbursable_account_id
            elif expense_group.fund_source == 'CCC':
                if configuration.name_in_journal_entry == 'MERCHANT':
                    vendor = None
                    merchant = lineitem.vendor if lineitem.vendor else ''
                    if merchant:
                        vendor = DestinationAttribute.objects.filter(
                            value__iexact=merchant, attribute_type='VENDOR', workspace_id=expense_group.workspace_id
                        ).first()
                    entity_id = vendor.destination_id if vendor else general_mappings.default_ccc_vendor_id
                else:
                    entity_id = employee_mapping.destination_employee.destination_id if employee_field_mapping == 'EMPLOYEE' \
                    else employee_mapping.destination_vendor.destination_id
                debit_account_id = get_ccc_account_id(configuration, general_mappings, lineitem, description)

            account = CategoryMapping.objects.filter(
                source_category__value=category,
                workspace_id=expense_group.workspace_id
            ).first()

            class_id = get_class_id_or_none(expense_group, lineitem)
            department_id = get_department_id_or_none(expense_group, lineitem)
            location_id = get_location_id_or_none(expense_group, lineitem)

            if not class_id and general_mappings.use_employee_class and employee_field_mapping == 'EMPLOYEE' and employee_mapping and employee_mapping.destination_employee:
                class_id = employee_mapping.destination_employee.detail.get('class_id')
            
            if not department_id and general_mappings.use_employee_department and general_mappings.department_level in ('ALL', 'TRANSACTION_LINE') \
                and employee_field_mapping == 'EMPLOYEE'and employee_mapping and employee_mapping.destination_employee:  
                if employee_mapping.destination_employee.detail.get('department_id'):
                    department_id = employee_mapping.destination_employee.detail.get('department_id')
            
            if not department_id:
                if general_mappings.department_id and general_mappings.department_level in ['TRANSACTION_LINE', 'ALL']:
                    department_id = general_mappings.department_id
            
            if not location_id and general_mappings.use_employee_location and general_mappings.location_level in ('ALL', 'TRANSACTION_LINE')\
                and employee_field_mapping == 'EMPLOYEE'and employee_mapping and employee_mapping.destination_employee:
                location_id = employee_mapping.destination_employee.detail.get('location_id')

            if not location_id and general_mappings.location_id:
                location_id = general_mappings.location_id

            custom_segments = get_custom_segments(expense_group, lineitem)

            journal_entry_lineitem_object, _ = JournalEntryLineItem.objects.update_or_create(
                journal_entry=journal_entry,
                expense_id=lineitem.id,
                defaults={
                    'debit_account_id': debit_account_id,
                    'account_id': account.destination_account.destination_id \
                        if account and account.destination_account else None,
                    'department_id': department_id,
                    'location_id': location_id,
                    'class_id': class_id if class_id else None,
                    'entity_id': entity_id,
                    'amount': lineitem.amount,
                    'tax_item_id': get_tax_item_id_or_none(expense_group, general_mappings,lineitem),
                    'tax_amount': lineitem.tax_amount,
                    'memo': get_expense_purpose(lineitem, category, configuration),
                    'netsuite_custom_segments': custom_segments
                }
            )

            journal_entry_lineitem_objects.append(journal_entry_lineitem_object)

        return journal_entry_lineitem_objects


class VendorPayment(models.Model):
    """
    NetSuite Vendor Payment
    """
    id = models.AutoField(primary_key=True)
    accounts_payable_id = models.CharField(max_length=255, help_text='NetSuite Accounts Payable Account id', null=True)
    account_id = models.CharField(max_length=255, help_text='NetSuite Account id', null=True)
    entity_id = models.CharField(max_length=255, help_text='NetSuite entity id ( Vendor / Employee )')
    currency = models.CharField(max_length=255, help_text='Vendor Payment Currency')
    department_id = models.CharField(max_length=255, help_text='NetSuite Department id', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite Location id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    subsidiary_id = models.CharField(max_length=255, help_text='NetSuite subsidiary id')
    external_id = models.CharField(max_length=255, unique=True, help_text='Fyle settlement id')
    memo = models.TextField(help_text='Vendor Payment Description', null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'vendor_payments'

    @staticmethod
    def create_vendor_payment(workspace_id, netsuite_object):
        """
        Create Vendor payment
        :return: vendor payment object
        """
        general_mappings = GeneralMapping.objects.get(workspace_id=workspace_id)
        configuration = Configuration.objects.get(workspace_id=workspace_id)

        vendor_payment_object = VendorPayment.objects.create(
            accounts_payable_id=general_mappings.reimbursable_account_id
            if configuration.reimbursable_expenses_object == 'EXPENSE REPORT'
            else general_mappings.accounts_payable_id,
            subsidiary_id=netsuite_object['subsidiary_id'],
            account_id=general_mappings.vendor_payment_account_id,
            entity_id=netsuite_object['entity_id'],
            currency=netsuite_object['currency'],
            memo=netsuite_object['memo'],
            external_id=netsuite_object['unique_id']
        )

        return vendor_payment_object


class VendorPaymentLineitem(models.Model):
    """
    NetSuite VendorPayment Lineitem
    """
    id = models.AutoField(primary_key=True)
    vendor_payment = models.ForeignKey(VendorPayment, on_delete=models.PROTECT, help_text='Reference to Vendor Payment')
    expense_group = models.OneToOneField(ExpenseGroup, on_delete=models.PROTECT, help_text='Reference to Expense Group')
    doc_id = models.CharField(max_length=255, help_text='NetSuite object internalId')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'vendor_payment_lineitems'

    @staticmethod
    def create_vendor_payment_lineitems(lines_payload, vendor_payment_object):
        """
        Create vendor payment lineitems
        :return: lineitems objects
        """
        vendor_payment_lineitem_objects = []

        for line in lines_payload:
            vendor_payment_lineitem_object = VendorPaymentLineitem.objects.create(
                vendor_payment=vendor_payment_object,
                expense_group=line['expense_group'],
                doc_id=line['internal_id']
            )

            vendor_payment_lineitem_objects.append(vendor_payment_lineitem_object)

        return vendor_payment_lineitem_objects
