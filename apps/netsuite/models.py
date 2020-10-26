"""
NetSuite models
"""
from datetime import datetime

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Q

from fyle_accounting_mappings.models import Mapping, MappingSetting, DestinationAttribute

from apps.fyle.models import ExpenseGroup, Expense, ExpenseAttribute
from apps.mappings.models import GeneralMapping, SubsidiaryMapping
from apps.workspaces.models import Workspace


def get_department_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    department_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='DEPARTMENT'
    ).first()

    department_id = None

    if department_setting:
        if lineitem:
            if department_setting.source_field == 'PROJECT':
                source_value = lineitem.project
            elif department_setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
            else:
                attribute = ExpenseAttribute.objects.filter(attribute_type=department_setting.source_field).first()
                source_value = lineitem.custom_properties.get(attribute.display_name, None)
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
        if lineitem:
            if class_setting.source_field == 'PROJECT':
                source_value = lineitem.project
            elif class_setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
            else:
                attribute = ExpenseAttribute.objects.filter(attribute_type=class_setting.source_field).first()
                source_value = lineitem.custom_properties.get(attribute.display_name, None)
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


def get_location_id_or_none(expense_group: ExpenseGroup, lineitem: Expense):
    location_setting: MappingSetting = MappingSetting.objects.filter(
        workspace_id=expense_group.workspace_id,
        destination_field='LOCATION'
    ).first()

    location_id = None

    if location_setting:
        if lineitem:
            if location_setting.source_field == 'PROJECT':
                source_value = lineitem.project
            elif location_setting.source_field == 'COST_CENTER':
                source_value = lineitem.cost_center
            else:
                attribute = ExpenseAttribute.objects.filter(attribute_type=location_setting.source_field).first()
                source_value = lineitem.custom_properties.get(attribute.display_name, None)
        else:
            source_value = expense_group.description[location_setting.source_field.lower()]

        mapping: Mapping = Mapping.objects.filter(
            source_type=location_setting.source_field,
            destination_type='LOCATION',
            source__value=source_value,
            workspace_id=expense_group.workspace_id
        ).first()

        if mapping:
            location_id = mapping.destination.destination_id
    return location_id


def get_transaction_date(expense_group: ExpenseGroup) -> str:
    if 'spent_at' in expense_group.description and expense_group.description['spent_at']:
        return expense_group.description['spent_at']
    elif 'approved_at' in expense_group.description and expense_group.description['approved_at']:
        return expense_group.description['approved_at']
    elif 'verified_at' in expense_group.description and expense_group.description['verified_at']:
        return expense_group.description['verified_at']

    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


def get_expense_purpose(lineitem, category) -> str:
    expense_purpose = ', purpose - {0}'.format(lineitem.purpose) if lineitem.purpose else ''
    spent_at = ' spent on {0} '.format(lineitem.spent_at.date()) if lineitem.spent_at else ''
    return 'Expense by {0} against category {1}{2}with claim number - {3}{4}'.format(
        lineitem.employee_email, category, spent_at, lineitem.claim_number, expense_purpose)


class CustomList(models.Model):
    """
    NetSuite Custom List
    """
    id = models.AutoField(primary_key=True)
    record_name = models.CharField(max_length=255, help_text='NetSuite Record Name')
    custom_type = models.CharField(max_length=255, help_text='NetSuite Custom Type')
    script_id = models.CharField(max_length=255, help_text='NetSuite Transaction Custom Field script id')
    internal_id = models.CharField(max_length=255, help_text='NetSuite Custom Record / Field internal id')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, help_text='Reference to Workspace model')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'custom_lists'


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
    transaction_date = models.DateTimeField(help_text='Bill transaction date')
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

        currency = DestinationAttribute.objects.filter(value=expense.currency,
                                                       workspace_id=expense_group.workspace_id,
                                                       attribute_type='CURRENCY').first()
        vendor_id = None
        if expense_group.fund_source == 'PERSONAL':
            vendor_id = Mapping.objects.get(
                source_type='EMPLOYEE',
                destination_type='VENDOR',
                source__value=description.get('employee_email'),
                workspace_id=expense_group.workspace_id
            ).destination.destination_id
        elif expense_group.fund_source == 'CCC':
            vendor_id = general_mappings.default_ccc_vendor_id

        bill_object, _ = Bill.objects.update_or_create(
            expense_group=expense_group,
            defaults={
                'subsidiary_id': subsidiary_mappings.internal_id,
                'accounts_payable_id': general_mappings.accounts_payable_id,
                'vendor_id': vendor_id,
                'location_id': general_mappings.location_id,
                'memo': 'Reimbursable expenses by {0}'.format(description.get('employee_email')) if
                expense_group.fund_source == 'PERSONAL' else
                'Credit card expenses by {0}'.format(description.get('employee_email')),
                'currency': currency.destination_id if currency else '1',
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
    account_id = models.CharField(max_length=255, help_text='NetSuite account id')
    location_id = models.CharField(max_length=255, help_text='NetSuite location id', null=True)
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    amount = models.FloatField(help_text='Bill amount')
    memo = models.CharField(max_length=255, help_text='NetSuite bill lineitem memo', null=True)
    custom_lists = JSONField(null=True)
    custom_properties = JSONField(null=True)
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
        default_list = ['CATEGORY', 'EMPLOYEE']

        for lineitem in expenses:
            category = lineitem.category if lineitem.category == lineitem.sub_category else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

            if expense_group.fund_source == 'CCC':
                account = Mapping.objects.filter(
                    source_type='CATEGORY',
                    source__value=category,
                    destination_type='CCC_ACCOUNT',
                    workspace_id=expense_group.workspace_id
                ).first()

            else:
                account = Mapping.objects.filter(
                    source_type='CATEGORY',
                    source__value=category,
                    destination_type='ACCOUNT',
                    workspace_id=expense_group.workspace_id
                ).first()

            class_id = get_class_id_or_none(expense_group, lineitem)

            department_id = get_department_id_or_none(expense_group, lineitem)

            location_id = get_location_id_or_none(expense_group, lineitem)

            if location_id is None:
                general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
                if general_mappings and general_mappings.location_id:
                    location_id = general_mappings.location_id

            mapping_settings = MappingSetting.objects.filter(workspace_id=expense_group.workspace_id).all()

            custom_list = []
            for setting in mapping_settings:
                if setting.source_field not in default_list:
                    attribute = ExpenseAttribute.objects.filter(attribute_type=setting.source_field).first()
                    source_value = lineitem.custom_properties.get(attribute.display_name, None)

                    mapping: Mapping = Mapping.objects.filter(
                        source_type=setting.source_field,
                        destination_type=setting.destination_field,
                        source__value=source_value,
                        workspace_id=expense_group.workspace_id
                    ).first()
                    if mapping:
                        cus_list = CustomList.objects.filter(
                            record_name=setting.destination_field,
                            workspace_id=expense_group.workspace_id
                        ).first()
                        if cus_list:
                            value = mapping.destination.destination_id
                            custom_list.append({
                                'scriptId': cus_list.script_id,
                                'type': 'Select',
                                'value': value
                            })

            bill_lineitem_object, _ = BillLineitem.objects.update_or_create(
                bill=bill,
                expense_id=lineitem.id,
                defaults={
                    'account_id': account.destination.destination_id if account else None,
                    'location_id': location_id if location_id else None,
                    'class_id': class_id,
                    'department_id': department_id,
                    'amount': lineitem.amount,
                    'memo': get_expense_purpose(lineitem, category),
                    'custom_lists': custom_list,
                    'custom_properties': lineitem.custom_properties
                }
            )

            bill_lineitem_objects.append(bill_lineitem_object)

        return bill_lineitem_objects


class ExpenseReport(models.Model):
    """
    NetSuite Expense Report
    """
    id = models.AutoField(primary_key=True)
    expense_group = models.OneToOneField(ExpenseGroup, on_delete=models.PROTECT, help_text='Expense group reference')
    account_id = models.CharField(max_length=255, help_text='NetSuite Account id')
    entity_id = models.CharField(max_length=255, help_text='NetSuite Entity id (Employee / Vendor)')
    currency = models.CharField(max_length=255, help_text='Expense Report Currency')
    department_id = models.CharField(max_length=255, help_text='NetSuite Department id', null=True)
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite Location id', null=True)
    subsidiary_id = models.CharField(max_length=255, help_text='NetSuite subsidiary id')
    memo = models.CharField(max_length=255, help_text='Expense Report Description')
    external_id = models.CharField(max_length=255, unique=True, help_text='Fyle reimbursement id')
    transaction_date = models.DateTimeField(help_text='Expense Report transaction date')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

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

        debit_account_id = None

        entity = Mapping.objects.get(
            destination_type='EMPLOYEE',
            source_type='EMPLOYEE',
            source__value=description.get('employee_email'),
            workspace_id=expense_group.workspace_id
        )

        if expense_group.fund_source == 'PERSONAL':
            debit_account_id = GeneralMapping.objects.get(
                workspace_id=expense_group.workspace_id).reimbursable_account_id
        elif expense_group.fund_source == 'CCC':
            debit_account_id = Mapping.objects.get(
                source_type='EMPLOYEE',
                destination_type='CREDIT_CARD_ACCOUNT',
                source__value=description.get('employee_email'),
                workspace_id=expense_group.workspace_id
            ).destination.destination_id

        expense_report_object, _ = ExpenseReport.objects.update_or_create(
            expense_group=expense_group,
            defaults={
                'account_id': debit_account_id,
                'entity_id': entity.destination.destination_id,
                'currency': expense.currency,
                'department_id': None,
                'class_id': None,
                'location_id': general_mappings.location_id,
                'subsidiary_id': subsidiary_mappings.internal_id,
                'memo': "Reimbursable expenses by {0}".format(description.get('employee_email')) if
                expense_group.fund_source == 'PERSONAL' else
                "Credit card expenses by {0}".format(description.get('employee_email')),
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
    category = models.CharField(max_length=255, help_text='NetSuite category account id')
    class_id = models.CharField(max_length=255, help_text='NetSuite Class id', null=True)
    customer_id = models.CharField(max_length=255, help_text='NetSuite Customer id', null=True)
    location_id = models.CharField(max_length=255, help_text='NetSuite location id', null=True)
    department_id = models.CharField(max_length=255, help_text='NetSuite department id', null=True)
    currency = models.CharField(max_length=255, help_text='NetSuite Currency id')
    memo = models.CharField(max_length=255, help_text='NetSuite bill lineitem memo', null=True)
    custom_lists = JSONField(null=True)
    custom_properties = JSONField(null=True)
    transaction_date = models.DateTimeField(help_text='Expense Report transaction date')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'expense_report_lineitems'

    @staticmethod
    def create_expense_report_lineitems(expense_group: ExpenseGroup):
        """
        Create expense report lineitems
        :param expense_group: expense group
        :return: lineitems objects
        """
        expenses = expense_group.expenses.all()
        expense_report = ExpenseReport.objects.get(expense_group=expense_group)

        expense_report_lineitem_objects = []
        default_list = ['CATEGORY', 'EMPLOYEE']

        for lineitem in expenses:
            category = lineitem.category if lineitem.category == lineitem.sub_category else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

            if expense_group.fund_source == 'CCC':
                account = Mapping.objects.filter(
                    source_type='CATEGORY',
                    source__value=category,
                    destination_type='CCC_ACCOUNT',
                    workspace_id=expense_group.workspace_id
                ).first()

            else:
                account = Mapping.objects.filter(
                    source_type='CATEGORY',
                    source__value=category,
                    destination_type='ACCOUNT',
                    workspace_id=expense_group.workspace_id
                ).first()

            currency = DestinationAttribute.objects.filter(value=lineitem.currency,
                                                           workspace_id=expense_group.workspace_id,
                                                           attribute_type='CURRENCY').first()

            class_id = get_class_id_or_none(expense_group, lineitem)

            department_id = get_department_id_or_none(expense_group, lineitem)

            location_id = get_location_id_or_none(expense_group, lineitem)

            if location_id is None:
                general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
                if general_mappings and general_mappings.location_id:
                    location_id = general_mappings.location_id

            mapping_settings = MappingSetting.objects.filter(workspace_id=expense_group.workspace_id).all()

            custom_list = []
            for setting in mapping_settings:
                if setting.source_field not in default_list:
                    attribute = ExpenseAttribute.objects.filter(attribute_type=setting.source_field).first()
                    source_value = lineitem.custom_properties.get(attribute.display_name, None)

                    mapping: Mapping = Mapping.objects.filter(
                        source_type=setting.source_field,
                        destination_type=setting.destination_field,
                        source__value=source_value,
                        workspace_id=expense_group.workspace_id
                    ).first()
                    if mapping:
                        cus_list = CustomList.objects.filter(
                            record_name=setting.destination_field,
                            workspace_id=expense_group.workspace_id
                        ).first()
                        if cus_list:
                            value = mapping.destination.destination_id
                            custom_list.append({
                                'scriptId': cus_list.script_id,
                                'type': 'Select',
                                'value': value
                            })

            expense_report_lineitem_object, _ = ExpenseReportLineItem.objects.update_or_create(
                expense_report=expense_report,
                expense_id=lineitem.id,
                defaults={
                    'amount': lineitem.amount,
                    'category': account.destination.destination_id,
                    'class_id': class_id if class_id else None,
                    'customer_id': None,
                    'location_id': location_id if location_id else None,
                    'department_id': department_id,
                    'currency': currency.destination_id if currency else '1',
                    'transaction_date': get_transaction_date(expense_group),
                    'memo': get_expense_purpose(lineitem, category),
                    'custom_lists': custom_list,
                    'custom_properties': lineitem.custom_properties
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
    subsidiary_id = models.CharField(max_length=255, help_text='NetSuite Subsidiary ID')
    memo = models.CharField(max_length=255, help_text='Journal Entry Memo')
    external_id = models.CharField(max_length=255, help_text='Journal Entry External ID')
    transaction_date = models.DateTimeField(help_text='Journal Entry transaction date')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

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

        journal_entry_object, _ = JournalEntry.objects.update_or_create(
            expense_group=expense_group,
            defaults={
                'currency': currency.destination_id if currency else '1',
                'subsidiary_id': subsidiary_mappings.internal_id,
                'memo': "Reimbursable expenses by {0}".format(description.get('employee_email')) if
                expense_group.fund_source == 'PERSONAL' else
                "Credit card expenses by {0}".format(description.get('employee_email')),
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
    memo = models.CharField(max_length=255, help_text='NetSuite JournalEntry lineitem description', null=True)
    custom_lists = JSONField(null=True)
    custom_properties = JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'journal_entry_lineitems'

    @staticmethod
    def create_journal_entry_lineitems(expense_group: ExpenseGroup):
        """
        Create Journal Entry Lineitems
        :param expense_group: expense group
        :return: lineitem objects
        """
        expenses = expense_group.expenses.all()
        journal_entry = JournalEntry.objects.get(expense_group=expense_group)

        description = expense_group.description

        debit_account_id = None

        entity = Mapping.objects.get(
            Q(destination_type='EMPLOYEE') | Q(destination_type='VENDOR'),
            source_type='EMPLOYEE',
            source__value=description.get('employee_email'),
            workspace_id=expense_group.workspace_id
        )

        if expense_group.fund_source == 'PERSONAL':
            if entity.destination_type == 'VENDOR':
                debit_account_id = GeneralMapping.objects.get(
                    workspace_id=expense_group.workspace_id).accounts_payable_id
            elif entity.destination_type == 'EMPLOYEE':
                debit_account_id = GeneralMapping.objects.get(
                    workspace_id=expense_group.workspace_id).reimbursable_account_id
        elif expense_group.fund_source == 'CCC':
            debit_account_id = Mapping.objects.get(
                source_type='EMPLOYEE',
                destination_type='CREDIT_CARD_ACCOUNT',
                source__value=description.get('employee_email'),
                workspace_id=expense_group.workspace_id
            ).destination.destination_id

        journal_entry_lineitem_objects = []
        default_list = ['CATEGORY', 'EMPLOYEE']

        for lineitem in expenses:
            category = lineitem.category if lineitem.category == lineitem.sub_category else '{0} / {1}'.format(
                lineitem.category, lineitem.sub_category)

            if expense_group.fund_source == 'CCC':
                account = Mapping.objects.filter(
                    source_type='CATEGORY',
                    source__value=category,
                    destination_type='CCC_ACCOUNT',
                    workspace_id=expense_group.workspace_id
                ).first()

            else:
                account = Mapping.objects.filter(
                    source_type='CATEGORY',
                    source__value=category,
                    destination_type='ACCOUNT',
                    workspace_id=expense_group.workspace_id
                ).first()

            class_id = get_class_id_or_none(expense_group, lineitem)

            department_id = get_department_id_or_none(expense_group, lineitem)

            location_id = get_location_id_or_none(expense_group, lineitem)

            if location_id is None:
                general_mappings = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
                if general_mappings and general_mappings.location_id:
                    location_id = general_mappings.location_id

            mapping_settings = MappingSetting.objects.filter(workspace_id=expense_group.workspace_id).all()

            custom_list = []
            for setting in mapping_settings:
                if setting.source_field not in default_list:
                    attribute = ExpenseAttribute.objects.filter(attribute_type=setting.source_field).first()
                    source_value = lineitem.custom_properties.get(attribute.display_name, None)

                    mapping: Mapping = Mapping.objects.filter(
                        source_type=setting.source_field,
                        destination_type=setting.destination_field,
                        source__value=source_value,
                        workspace_id=expense_group.workspace_id
                    ).first()
                    if mapping:
                        cus_list = CustomList.objects.filter(
                            record_name=setting.destination_field,
                            workspace_id=expense_group.workspace_id
                        ).first()
                        if cus_list:
                            value = mapping.destination.destination_id
                            custom_list.append({
                                'scriptId': cus_list.script_id,
                                'type': 'Select',
                                'value': value
                            })

            journal_entry_lineitem_object, _ = JournalEntryLineItem.objects.update_or_create(
                journal_entry=journal_entry,
                expense_id=lineitem.id,
                defaults={
                    'debit_account_id': debit_account_id,
                    'account_id': account.destination.destination_id,
                    'department_id': department_id,
                    'location_id': location_id if location_id else None,
                    'class_id': class_id if class_id else None,
                    'entity_id': entity.destination.destination_id,
                    'amount': lineitem.amount,
                    'memo': get_expense_purpose(lineitem, category),
                    'custom_lists': custom_list,
                    'custom_properties': lineitem.custom_properties
                }
            )

            journal_entry_lineitem_objects.append(journal_entry_lineitem_object)

        return journal_entry_lineitem_objects
