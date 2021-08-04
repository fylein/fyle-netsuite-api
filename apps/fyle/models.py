"""
Fyle Models
"""
import dateutil.parser
from typing import List, Dict
from datetime import datetime

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import JSONField, ArrayField
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.db import models
from django.db.models import Count, Q

from fyle_accounting_mappings.models import ExpenseAttribute

from apps.workspaces.models import Workspace, Configuration

ALLOWED_FIELDS = [
    'employee_email', 'report_id', 'claim_number', 'settlement_id',
    'fund_source', 'vendor', 'category', 'project', 'cost_center',
    'verified_at', 'approved_at', 'spent_at', 'expense_id'
]


ALLOWED_FORM_INPUT = {
    'group_expenses_by': ['settlement_id', 'claim_number', 'report_id', 'category', 'vendor', 'expense_id'],
    'export_date_type': ['current_date', 'approved_at', 'spent_at', 'verified_at', 'last_spent_at']
}


def _format_date(date_string: str) -> str:
    if date_string:
        date_string = dateutil.parser.parse(date_string).strftime('%Y-%m-%dT00:00:00.000Z')
    return date_string


class Expense(models.Model):
    """
    Expense
    """
    id = models.AutoField(primary_key=True)
    employee_email = models.EmailField(max_length=255, unique=False, help_text='Email id of the Fyle employee')
    category = models.CharField(max_length=255, null=True, blank=True, help_text='Fyle Expense Category')
    sub_category = models.CharField(max_length=255, null=True, blank=True, help_text='Fyle Expense Sub-Category')
    project = models.CharField(max_length=255, null=True, blank=True, help_text='Project')
    org_id = models.CharField(max_length=255, null=True, help_text='Organization ID')
    expense_id = models.CharField(max_length=255, unique=True, help_text='Expense ID')
    expense_number = models.CharField(max_length=255, help_text='Expense Number')
    claim_number = models.CharField(max_length=255, help_text='Claim Number', null=True)
    amount = models.FloatField(help_text='Home Amount')
    currency = models.CharField(max_length=5, help_text='Home Currency')
    foreign_amount = models.FloatField(null=True, help_text='Foreign Amount')
    foreign_currency = models.CharField(null=True, max_length=5, help_text='Foreign Currency')
    settlement_id = models.CharField(max_length=255, help_text='Settlement ID', null=True)
    reimbursable = models.BooleanField(default=False, help_text='Expense reimbursable or not')
    billable = models.BooleanField(null=True, help_text='Expense Billable or not')
    exported = models.BooleanField(default=False, help_text='Expense exported or not')
    state = models.CharField(max_length=255, help_text='Expense state')
    vendor = models.CharField(max_length=255, null=True, blank=True, help_text='Vendor')
    cost_center = models.CharField(max_length=255, null=True, blank=True, help_text='Fyle Expense Cost Center')
    purpose = models.TextField(null=True, blank=True, help_text='Purpose')
    report_id = models.CharField(max_length=255, help_text='Report ID')
    spent_at = models.DateTimeField(null=True, help_text='Expense spent at')
    approved_at = models.DateTimeField(null=True, help_text='Expense approved at')
    expense_created_at = models.DateTimeField(help_text='Expense created at')
    expense_updated_at = models.DateTimeField(help_text='Expense created at')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
    fund_source = models.CharField(max_length=255, help_text='Expense fund source')
    verified_at = models.DateTimeField(help_text='Report verified at', null=True)
    paid_on_netsuite = models.BooleanField(help_text='Expense Payment status on NetSuite', default=False)
    custom_properties = JSONField(null=True)

    class Meta:
        db_table = 'expenses'

    @staticmethod
    def create_expense_objects(expenses: List[Dict], workspace_id: int):
        """
        Bulk create expense objects
        """
        expense_objects = []

        custom_properties = ExpenseAttribute.objects.filter(
            ~Q(attribute_type='EMPLOYEE') & ~Q(attribute_type='CATEGORY'),
            ~Q(attribute_type='PROJECT') & ~Q(attribute_type='COST_CENTER'),
            workspace_id=workspace_id
        ).values('display_name').distinct()

        custom_property_keys = list(set([prop['display_name'].lower() for prop in custom_properties]))

        for expense in expenses:
            expense_custom_properties = {}

            if custom_property_keys and expense['custom_properties']:
                for prop in expense['custom_properties']:
                    if prop['name'].lower() in custom_property_keys:
                        expense_custom_properties[prop['name']] = prop['value']

            expense_object, _ = Expense.objects.update_or_create(
                expense_id=expense['id'],
                defaults={
                    'org_id': expense['org_id'],
                    'employee_email': expense['employee_email'],
                    'category': expense['category_name'],
                    'sub_category': expense['sub_category'],
                    'project': expense['project_name'],
                    'expense_number': expense['expense_number'],
                    'claim_number': expense['claim_number'],
                    'amount': round(expense['amount'], 2),
                    'currency': expense['currency'],
                    'foreign_amount': expense['foreign_amount'],
                    'foreign_currency': expense['foreign_currency'],
                    'settlement_id': expense['settlement_id'],
                    'reimbursable': expense['reimbursable'],
                    'billable': expense['billable'] if expense['billable'] else None,
                    'exported': expense['exported'],
                    'state': expense['state'],
                    'vendor': expense['vendor'],
                    'cost_center': expense['cost_center_name'],
                    'purpose': expense['purpose'],
                    'report_id': expense['report_id'],
                    'spent_at': _format_date(expense['spent_at']),
                    'approved_at': _format_date(expense['approved_at']),
                    'expense_created_at': expense['created_at'],
                    'expense_updated_at': expense['updated_at'],
                    'fund_source': expense['fund_source'],
                    'verified_at': _format_date(expense['verified_at']),
                    'custom_properties': expense_custom_properties if expense_custom_properties else {}
                }
            )

            if not ExpenseGroup.objects.filter(expenses__id=expense_object.id).first():
                expense_objects.append(expense_object)

        return expense_objects


def get_default_expense_group_fields():
    return ['employee_email', 'report_id', 'claim_number', 'fund_source']


def get_default_expense_state():
    return 'PAYMENT_PROCESSING'


class ExpenseGroupSettings(models.Model):
    """
    ExpenseGroupCustomizationSettings
    """
    id = models.AutoField(primary_key=True)
    reimbursable_expense_group_fields = ArrayField(
        base_field=models.CharField(max_length=100), default=get_default_expense_group_fields,
        help_text='list of fields reimbursable expense grouped by'
    )

    corporate_credit_card_expense_group_fields = ArrayField(
        base_field=models.CharField(max_length=100), default=get_default_expense_group_fields,
        help_text='list of fields ccc expenses grouped by'
    )
    expense_state = models.CharField(
        max_length=100, default=get_default_expense_state,
        help_text='state at which the expenses are fetched ( PAYMENT_PENDING / PAYMENT_PROCESSING / PAID)')
    export_date_type = models.CharField(max_length=100, default='current_date', help_text='Export Date')
    workspace = models.OneToOneField(
        Workspace, on_delete=models.PROTECT, help_text='To which workspace this expense group setting belongs to'
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'expense_group_settings'

    @staticmethod
    def update_expense_group_settings(expense_group_settings: Dict, workspace_id: int):
        configuration: Configuration = Configuration.objects.get(workspace_id=workspace_id)
        settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
        current_reimbursable_settings = list(settings.reimbursable_expense_group_fields)
        current_ccc_settings = list(settings.corporate_credit_card_expense_group_fields)

        reimbursable_grouped_by = []
        corporate_credit_card_expenses_grouped_by = []

        immutable_reimbursable_list = tuple(current_reimbursable_settings)
        immutable_ccc_list = tuple(current_ccc_settings)

        for field in immutable_reimbursable_list:
            if field in ALLOWED_FORM_INPUT['group_expenses_by']:
                current_reimbursable_settings.remove(field)

        for field in immutable_ccc_list:
            if field in ALLOWED_FORM_INPUT['group_expenses_by']:
                if field == 'expense_id' and configuration.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE':
                    pass
                else:
                    current_ccc_settings.remove(field)

        if 'report_id' not in current_reimbursable_settings:
            if 'claim_number' in current_reimbursable_settings:
                current_reimbursable_settings.remove('claim_number')
        else:
            current_reimbursable_settings.append('claim_number')

        if 'report_id' not in current_ccc_settings:
            if 'claim_number' in current_ccc_settings:
                current_ccc_settings.remove('claim_number')
        else:
            current_ccc_settings.append('claim_number')

        reimbursable_grouped_by.extend(current_reimbursable_settings)
        corporate_credit_card_expenses_grouped_by.extend(current_ccc_settings)

        reimbursable_grouped_by.extend(expense_group_settings['expenses_grouped_by'])
        corporate_credit_card_expenses_grouped_by.extend(expense_group_settings['expenses_grouped_by'])

        reimbursable_grouped_by = list(set(reimbursable_grouped_by))
        corporate_credit_card_expenses_grouped_by = list(set(corporate_credit_card_expenses_grouped_by))

        for field in ALLOWED_FORM_INPUT['export_date_type']:
            if field in reimbursable_grouped_by:
                reimbursable_grouped_by.remove(field)

        for field in ALLOWED_FORM_INPUT['export_date_type']:
            if field in corporate_credit_card_expenses_grouped_by:
                corporate_credit_card_expenses_grouped_by.remove(field)

        if expense_group_settings['export_date_type'] != 'current_date':
            reimbursable_grouped_by.append(expense_group_settings['export_date_type'])
            corporate_credit_card_expenses_grouped_by.append(expense_group_settings['export_date_type'])

        if 'claim_number' in reimbursable_grouped_by and corporate_credit_card_expenses_grouped_by:
            reimbursable_grouped_by.append('report_id')
            corporate_credit_card_expenses_grouped_by.append('report_id')

        return ExpenseGroupSettings.objects.update_or_create(
            workspace_id=workspace_id,
            defaults={
                'reimbursable_expense_group_fields': reimbursable_grouped_by,
                'corporate_credit_card_expense_group_fields': corporate_credit_card_expenses_grouped_by,
                'expense_state': expense_group_settings['expense_state'],
                'export_date_type': expense_group_settings['export_date_type']
            }
        )


def _group_expenses(expenses, group_fields, workspace_id):
    expense_ids = list(map(lambda expense: expense.id, expenses))
    expenses = Expense.objects.filter(id__in=expense_ids).all()

    custom_fields = {}

    for field in group_fields:
        if field.lower() not in ALLOWED_FIELDS:
            group_fields.pop(group_fields.index(field))
            field = ExpenseAttribute.objects.filter(workspace_id=workspace_id,
                                                    attribute_type=field.upper()).first()
            if field:
                custom_fields[field.attribute_type.lower()] = KeyTextTransform(field.display_name, 'custom_properties')

    expense_groups = list(
        expenses.values(*group_fields, **custom_fields).annotate(total=Count('*'), expense_ids=ArrayAgg('id')))
    return expense_groups


class ExpenseGroup(models.Model):
    """
    Expense Group
    """
    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT,
                                  help_text='To which workspace this expense group belongs to')
    fund_source = models.CharField(max_length=255, help_text='Expense fund source')
    expenses = models.ManyToManyField(Expense, help_text="Expenses under this Expense Group")
    description = JSONField(max_length=255, help_text='Description', null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    exported_at = models.DateTimeField(help_text='Exported at', null=True)
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'expense_groups'

    @staticmethod
    def create_expense_groups_by_report_id_fund_source(expense_objects: List[Expense], workspace_id):
        """
        Group expense by report_id and fund_source
        """
        expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)

        reimbursable_expense_group_fields = expense_group_settings.reimbursable_expense_group_fields
        reimbursable_expenses = list(filter(lambda expense: expense.fund_source == 'PERSONAL', expense_objects))

        expense_groups = _group_expenses(reimbursable_expenses, reimbursable_expense_group_fields, workspace_id)

        corporate_credit_card_expense_group_field = expense_group_settings.corporate_credit_card_expense_group_fields
        corporate_credit_card_expenses = list(filter(lambda expense: expense.fund_source == 'CCC', expense_objects))
        corporate_credit_card_expense_groups = _group_expenses(
            corporate_credit_card_expenses, corporate_credit_card_expense_group_field, workspace_id)

        expense_groups.extend(corporate_credit_card_expense_groups)

        for expense_group in expense_groups:
            if expense_group_settings.export_date_type == 'last_spent_at':
                expense_group['last_spent_at'] = Expense.objects.filter(
                    id__in=expense_group['expense_ids']).order_by('-spent_at').first().spent_at

            expense_ids = expense_group['expense_ids']
            expense_group.pop('total')
            expense_group.pop('expense_ids')

            for key in expense_group:
                if key in ALLOWED_FORM_INPUT['export_date_type']:
                    if expense_group[key]:
                        expense_group[key] = expense_group[key].strftime('%Y-%m-%dT%H:%M:%S')
                    else:
                        expense_group[key] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

            expense_group_object = ExpenseGroup.objects.create(
                workspace_id=workspace_id,
                fund_source=expense_group['fund_source'],
                description=expense_group
            )

            expense_group_object.expenses.add(*expense_ids)


class Reimbursement(models.Model):
    """
    Reimbursements
    """
    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, help_text='To which workspace this reimbursement belongs to'
    )
    settlement_id = models.CharField(max_length=255, help_text='Fyle Settlement ID')
    reimbursement_id = models.CharField(max_length=255, help_text='Fyle Reimbursement ID')
    state = models.CharField(max_length=255, help_text='Fyle Reimbursement State')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'reimbursements'

    @staticmethod
    def create_or_update_reimbursement_objects(reimbursements: List[Dict], workspace_id):
        """
        Create or Update reimbursement attributes
        """
        reimbursement_id_list = [reimbursement['id'] for reimbursement in reimbursements]
        existing_reimbursements = Reimbursement.objects.filter(
            reimbursement_id__in=reimbursement_id_list, workspace_id=workspace_id).all()

        existing_reimbursement_ids = []
        primary_key_map = {}

        for existing_reimbursement in existing_reimbursements:
            existing_reimbursement_ids.append(existing_reimbursement.reimbursement_id)
            primary_key_map[existing_reimbursement.reimbursement_id] = {
                'id': existing_reimbursement.id,
                'state': existing_reimbursement.state
            }

        attributes_to_be_created = []
        attributes_to_be_updated = []

        for reimbursement in reimbursements:
            if reimbursement['id'] not in existing_reimbursement_ids:
                attributes_to_be_created.append(
                    Reimbursement(
                        settlement_id=reimbursement['settlement_id'],
                        reimbursement_id=reimbursement['id'],
                        state=reimbursement['state'],
                        workspace_id=workspace_id
                    )
                )
            else:
                if reimbursement['state'] != primary_key_map[reimbursement['id']]['state']:
                    attributes_to_be_updated.append(
                        Reimbursement(
                            id=primary_key_map[reimbursement['id']]['id'],
                            state=reimbursement['state']
                        )
                    )

        if attributes_to_be_created:
            Reimbursement.objects.bulk_create(attributes_to_be_created, batch_size=50)

        if attributes_to_be_updated:
            Reimbursement.objects.bulk_update(attributes_to_be_updated, fields=['state'], batch_size=50)
