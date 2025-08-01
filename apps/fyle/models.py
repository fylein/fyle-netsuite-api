"""
Fyle Models
"""
import logging
from dateutil import parser
from typing import List, Dict
from datetime import datetime, timezone
from collections import defaultdict


from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models.fields.json import KeyTextTransform
from django.db import models
from django.db.models import Count, Q, JSONField

from fyle_accounting_mappings.models import ExpenseAttribute
from fyle_accounting_mappings.mixins import AutoAddCreateUpdateInfoMixin
from fyle_accounting_library.fyle_platform.constants import IMPORTED_FROM_CHOICES
from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum

from apps.workspaces.models import Configuration, Workspace

logger = logging.getLogger(__name__)
logger.level = logging.INFO


ALLOWED_FIELDS = [
    'employee_email', 'report_id', 'claim_number', 'settlement_id',
    'fund_source', 'vendor', 'category', 'project', 'cost_center',
    'verified_at', 'approved_at', 'spent_at', 'expense_id', 'posted_at',
    'bank_transaction_id'
]


ALLOWED_FORM_INPUT = {
    'group_expenses_by': ['settlement_id', 'claim_number', 'report_id', 'category', 'vendor', 'expense_id'],
    'export_date_type': ['current_date', 'approved_at', 'spent_at', 'verified_at', 'last_spent_at', 'posted_at']
}

SOURCE_ACCOUNT_MAP = {
    'PERSONAL_CASH_ACCOUNT': 'PERSONAL',
    'PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT': 'CCC'
}

CCC_EXPENSE_STATE = (
    ('APPROVED', 'APPROVED'),
    ('PAID', 'PAID'),
    ('PAYMENT_PROCESSING', 'PAYMENT_PROCESSING')
)

EXPENSE_FILTER_RANK = (
    (1, 1),
    (2, 2)
)

EXPENSE_FILTER_JOIN_BY = (
    ('AND', 'AND'),
    ('OR', 'OR')
)

EXPENSE_FILTER_CUSTOM_FIELD_TYPE = (
    ('SELECT', 'SELECT'),
    ('NUMBER', 'NUMBER'),
    ('TEXT','TEXT'),
    ('BOOLEAN', 'BOOLEAN')
)

EXPENSE_FILTER_OPERATOR = (
	('isnull', 'isnull'),
	('in', 'in'),
	('iexact' , 'iexact'),
	('icontains', 'icontains'),
	('lt', 'lt'),
	('lte', 'lte'),
    ('not_in', 'not_in')
)

SPLIT_EXPENSE_GROUPING = (('SINGLE_LINE_ITEM', 'SINGLE_LINE_ITEM'), ('MULTIPLE_LINE_ITEM', 'MULTIPLE_LINE_ITEM'))

class Expense(models.Model):
    """
    Expense
    """
    id = models.AutoField(primary_key=True)
    employee_email = models.EmailField(max_length=255, unique=False, help_text='Email id of the Fyle employee')
    employee_name = models.CharField(max_length=255, null=True, help_text='Name of the Fyle employee')
    category = models.CharField(max_length=255, null=True, blank=True, help_text='Fyle Expense Category')
    sub_category = models.CharField(max_length=255, null=True, blank=True, help_text='Fyle Expense Sub-Category')
    project = models.CharField(max_length=255, null=True, blank=True, help_text='Project')
    project_id = models.CharField(max_length=255, null=True, blank=True, help_text='Project ID')
    org_id = models.CharField(max_length=255, null=True, help_text='Organization ID')
    expense_id = models.CharField(max_length=255, unique=True, help_text='Expense ID')
    expense_number = models.CharField(max_length=255, help_text='Expense Number')
    claim_number = models.CharField(max_length=255, help_text='Claim Number', null=True)
    amount = models.FloatField(help_text='Home Amount')
    currency = models.CharField(max_length=5, help_text='Home Currency')
    foreign_amount = models.FloatField(null=True, help_text='Foreign Amount')
    foreign_currency = models.CharField(null=True, max_length=5, help_text='Foreign Currency')
    tax_amount = models.FloatField(null=True, help_text="Tax Amount")
    tax_group_id = models.CharField(null=True, max_length=255, help_text="Tax Group ID")
    settlement_id = models.CharField(max_length=255, help_text='Settlement ID', null=True)
    reimbursable = models.BooleanField(default=False, help_text='Expense reimbursable or not')
    billable = models.BooleanField(null=True, help_text='Expense Billable or not')
    state = models.CharField(max_length=255, help_text='Expense state')
    vendor = models.CharField(max_length=255, null=True, blank=True, help_text='Vendor')
    cost_center = models.CharField(max_length=255, null=True, blank=True, help_text='Fyle Expense Cost Center')
    purpose = models.TextField(null=True, blank=True, help_text='Purpose')
    report_id = models.CharField(max_length=255, help_text='Report ID')
    imported_from = models.CharField(choices=IMPORTED_FROM_CHOICES, max_length=255, help_text='Imported from source', null=True)
    report_title = models.TextField(null=True, blank=True, help_text='Report title')
    corporate_card_id = models.CharField(max_length=255, null=True, blank=True, help_text='Corporate Card ID')
    bank_transaction_id = models.CharField(max_length=255, null=True, blank=True, help_text='Bank Transaction ID')
    file_ids = ArrayField(base_field=models.CharField(max_length=255), null=True, help_text='File IDs')
    spent_at = models.DateTimeField(null=True, help_text='Expense spent at')
    approved_at = models.DateTimeField(null=True, help_text='Expense approved at')
    posted_at = models.DateTimeField(null=True, help_text='Date when the money is taken from the bank')
    is_posted_at_null = models.BooleanField(default=False, help_text='Flag check if posted at is null or not')
    expense_created_at = models.DateTimeField(help_text='Expense created at')
    expense_updated_at = models.DateTimeField(help_text='Expense created at')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')
    fund_source = models.CharField(max_length=255, help_text='Expense fund source')
    verified_at = models.DateTimeField(help_text='Report verified at', null=True)
    paid_on_netsuite = models.BooleanField(help_text='Expense Payment status on NetSuite', default=False)
    paid_on_fyle = models.BooleanField(help_text='Expense Payment status on Fyle', default=False)
    custom_properties = JSONField(null=True)
    is_skipped = models.BooleanField(null=True, default=False, help_text='Expense is skipped or not')
    accounting_export_summary = JSONField(default=dict)
    masked_corporate_card_number = models.CharField(max_length=255, help_text='Masked Corporate Card Number', null=True)
    previous_export_state = models.CharField(max_length=255, help_text='Previous export state', null=True)
    workspace = models.ForeignKey(
            Workspace, on_delete=models.PROTECT, help_text='To which workspace this expense belongs to', null=True
        )

    class Meta:
        db_table = 'expenses'
        indexes = [
            models.Index(fields=['accounting_export_summary', 'workspace_id']),
            models.Index(fields=['fund_source', 'workspace_id'])
        ]

    @staticmethod
    def create_expense_objects(expenses: List[Dict], workspace_id, skip_update: bool = False, imported_from: ExpenseImportSourceEnum = None):
        """
        Bulk create expense objects
        """

        expense_objects = []

        for expense in expenses:
            for custom_property_field in expense['custom_properties']:
                if expense['custom_properties'][custom_property_field] == '':
                    expense['custom_properties'][custom_property_field] = None

            expense_data_to_append = None
            if not skip_update:
                expense_data_to_append = {
                    'claim_number': expense['claim_number'],
                    'report_title': expense['report_title'],
                    'approved_at': expense['approved_at'],
                    'expense_created_at': expense['expense_created_at'],
                    'expense_updated_at': expense['expense_updated_at']
                }

            defaults = {
                'employee_email': expense['employee_email'],
                'employee_name': expense['employee_name'],
                'category': expense['category'],
                'sub_category': expense['sub_category'],
                'project': expense['project'],
                'project_id': expense['project_id'],
                'expense_number': expense['expense_number'],
                'org_id': expense['org_id'],
                'tax_amount': round(expense['tax_amount'], 2) if expense['tax_amount'] else 0,
                'tax_group_id': expense['tax_group_id'],
                'amount': round(expense['amount'], 2),
                'currency': expense['currency'],
                'foreign_amount': expense['foreign_amount'],
                'foreign_currency': expense['foreign_currency'],
                'reimbursable': expense['reimbursable'],
                'billable': expense['billable'],
                'state': expense['state'],
                'vendor': expense['vendor'][:250] if expense['vendor'] else None,
                'cost_center': expense['cost_center'],
                'purpose': expense['purpose'],
                'report_id': expense['report_id'],
                'corporate_card_id': expense['corporate_card_id'],
                'bank_transaction_id': expense['bank_transaction_id'],
                'file_ids': expense['file_ids'],
                'spent_at': expense['spent_at'],
                'posted_at': expense['posted_at'],
                'is_posted_at_null': expense['is_posted_at_null'],
                'fund_source': SOURCE_ACCOUNT_MAP[expense['source_account_type']],
                'verified_at': expense['verified_at'],
                'custom_properties': expense['custom_properties'],
                'workspace_id': workspace_id
            }

            if expense_data_to_append:
                defaults.update(expense_data_to_append)

            expense_object, created = Expense.objects.update_or_create(
                expense_id=expense['id'],
                defaults=defaults
            )

            # Only set imported_from for newly created expenses
            if created and imported_from:
                expense_object.imported_from = imported_from
                expense_object.save(
                    update_fields=['imported_from']
                )
            
            if (not expense_object.is_skipped and not ExpenseGroup.objects.filter(expenses__id=expense_object.id).first()):
                expense_objects.append(expense_object)

        return expense_objects


def get_default_expense_group_fields():
    return ['employee_email', 'report_id', 'claim_number', 'fund_source']


def get_default_expense_state():
    return 'PAYMENT_PROCESSING'

def get_default_ccc_expense_state():
    return 'PAID'

def get_default_split_expense_grouping():
    return 'MULTIPLE_LINE_ITEM'


class ExpenseGroupSettings(AutoAddCreateUpdateInfoMixin, models.Model):
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
        help_text='state at which the expenses are fetched ( PAYMENT_PENDING / PAYMENT_PROCESSING / PAID)',
        null=True)
    ccc_expense_state = models.CharField(
        max_length=100, default=get_default_ccc_expense_state, choices=CCC_EXPENSE_STATE,
        help_text='state at which the ccc expenses are fetched (APPROVED/PAID)', null=True)
    reimbursable_export_date_type = models.CharField(max_length=100, default='current_date', help_text='Export Date')
    ccc_export_date_type = models.CharField(max_length=100, default='current_date', help_text='CCC Export Date')
    import_card_credits = models.BooleanField(help_text='Import Card Credits', default=False)
    split_expense_grouping = models.CharField(
        max_length=100,
        default=get_default_split_expense_grouping,
        choices=SPLIT_EXPENSE_GROUPING, help_text='specify line items for split expenses grouping'
    )
    workspace = models.OneToOneField(
        Workspace, on_delete=models.PROTECT, help_text='To which workspace this expense group setting belongs to', 
        related_name = 'expense_group_settings'
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'expense_group_settings'

    @staticmethod
    def update_expense_group_settings(expense_group_settings: Dict, workspace_id: int, user):
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

        reimbursable_grouped_by.extend(expense_group_settings['reimbursable_expense_group_fields'])
        corporate_credit_card_expenses_grouped_by.extend(
            expense_group_settings['corporate_credit_card_expense_group_fields']
        )

        reimbursable_grouped_by = list(set(reimbursable_grouped_by))
        corporate_credit_card_expenses_grouped_by = list(set(corporate_credit_card_expenses_grouped_by))

        for field in ALLOWED_FORM_INPUT['export_date_type']:
            if field in reimbursable_grouped_by:
                reimbursable_grouped_by.remove(field)

        for field in ALLOWED_FORM_INPUT['export_date_type']:
            if field in corporate_credit_card_expenses_grouped_by:
                corporate_credit_card_expenses_grouped_by.remove(field)

        if expense_group_settings['reimbursable_export_date_type'] != 'current_date':
            reimbursable_grouped_by.append(expense_group_settings['reimbursable_export_date_type'])

        if expense_group_settings['ccc_export_date_type'] != 'current_date':
            corporate_credit_card_expenses_grouped_by.append(expense_group_settings['ccc_export_date_type'])

        if 'claim_number' in reimbursable_grouped_by and corporate_credit_card_expenses_grouped_by:
            reimbursable_grouped_by.append('report_id')
            corporate_credit_card_expenses_grouped_by.append('report_id')

        return ExpenseGroupSettings.objects.update_or_create(
            workspace_id=workspace_id,
            defaults={
                'reimbursable_expense_group_fields': reimbursable_grouped_by,
                'corporate_credit_card_expense_group_fields': corporate_credit_card_expenses_grouped_by,
                'expense_state': expense_group_settings['expense_state'],
                'ccc_expense_state': expense_group_settings['ccc_expense_state'],
                'reimbursable_export_date_type': expense_group_settings['reimbursable_export_date_type'],
                'ccc_export_date_type': expense_group_settings['ccc_export_date_type'],
                'split_expense_grouping': expense_group_settings['split_expense_grouping']
            },
            user=user
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


def filter_expense_groups(
    expense_groups,
    expenses: Expense,
    expense_group_fields,
    reimbursable_export_type=None,
    ccc_export_type=None,
):

    filtered_expense_groups = []
    skipped_expense_ids = []

    for expense_group in expense_groups:
        expense_group_expenses_ids = expense_group['expense_ids']
        filtered_expenses = [
            item for item in expenses if item.id in expense_group_expenses_ids
        ]
        if 'expense_id' not in expense_group_fields and (
            reimbursable_export_type in ('EXPENSE REPORT', 'BILL') or ccc_export_type == 'BILL'
        ):
            total_amount = 0
            if "spent_at" in expense_group_fields:
                grouped_data = defaultdict(list)
                for expense in filtered_expenses:
                    spent_at = expense.spent_at
                    grouped_data[spent_at].append(expense)
                grouped_expenses = list(grouped_data.values())
                expense_groups = []
                for group_expense in grouped_expenses:
                    total_amount = 0
                    for expense in group_expense:
                        total_amount += expense.amount
                    if total_amount < 0:
                        skipped_expense_ids.extend([expense.id for expense in group_expense if expense.amount < 0])
                        filtered_expenses = list(
                            filter(lambda expense: expense.amount > 0, group_expense)
                        )
            else:
                for expense in filtered_expenses:
                    total_amount += expense.amount

                if total_amount < 0:
                    skipped_expense_ids.extend([expense.id for expense in filtered_expenses if expense.amount < 0])
                    filtered_expenses = list(
                        filter(lambda expense: expense.amount > 0, filtered_expenses)
                    )
        elif reimbursable_export_type not in ['JOURNAL ENTRY'] or ccc_export_type == 'BILL':
            skipped_expense_ids.extend([expense.id for expense in filtered_expenses if expense.amount < 0])
            filtered_expenses = list(
                filter(lambda expense: expense.amount > 0, filtered_expenses)
            )

        filtered_expense_ids = [item.id for item in filtered_expenses]

        if len(filtered_expense_ids) != 0:
            expense_group['expense_ids'] = filtered_expense_ids
            filtered_expense_groups.append(expense_group)

    return filtered_expense_groups, skipped_expense_ids


class ExpenseGroup(models.Model):
    """
    Expense Group
    """
    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT,
                                  help_text='To which workspace this expense group belongs to')
    fund_source = models.CharField(max_length=255, help_text='Expense fund source')
    expenses = models.ManyToManyField(Expense, help_text="Expenses under this Expense Group")
    employee_name = models.CharField(max_length=255, help_text='Expense Group Employee Name', null=True)
    description = JSONField(max_length=255, help_text='Description', null=True)
    response_logs = JSONField(help_text='Reponse log of the export', null=True)
    export_url = models.CharField(max_length=255, help_text='Netsuite URL for the exported expenses', null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    exported_at = models.DateTimeField(help_text='Exported at', null=True)
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'expense_groups'

    @staticmethod
    def create_expense_groups_by_report_id_fund_source(expense_objects: List[Expense], configuration: Configuration, workspace_id):
        """
        Group expense by report_id and fund_source
        """
        expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
        expense_groups = []
        filtered_corporate_credit_card_expense_groups = []
        skipped_expense_ids = []

        # Group Reimbursable Expenses
        reimbursable_expense_group_fields = expense_group_settings.reimbursable_expense_group_fields

        reimbursable_expenses = list(filter(lambda expense: expense.fund_source == 'PERSONAL', expense_objects))

        reimbursable_expense_groups = _group_expenses(reimbursable_expenses, reimbursable_expense_group_fields, workspace_id)

        filtered_reimbursable_expense_groups, reimbursable_skipped_expense_ids = filter_expense_groups(
            reimbursable_expense_groups,
            reimbursable_expenses,
            reimbursable_expense_group_fields,
            configuration.reimbursable_expenses_object,
            None
        )
        skipped_expense_ids.extend(reimbursable_skipped_expense_ids)

        expense_groups.extend(filtered_reimbursable_expense_groups)

        # Group CCC Expenses
        corporate_credit_card_expense_group_field = expense_group_settings.corporate_credit_card_expense_group_fields

        corporate_credit_card_expenses = list(filter(lambda expense: expense.fund_source == 'CCC', expense_objects))

        if corporate_credit_card_expenses:
            # Group split Credit Card Charges by `bank_transaction_id`
            if (
                configuration.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE' and
                expense_group_settings.split_expense_grouping == 'MULTIPLE_LINE_ITEM'
            ):
                ccc_expenses_without_bank_transaction_id = list(
                    filter(lambda expense: not expense.bank_transaction_id, corporate_credit_card_expenses)
                )

                ccc_expenses_with_bank_transaction_id = list(
                    filter(lambda expense: expense.bank_transaction_id, corporate_credit_card_expenses)
                )

                if ccc_expenses_without_bank_transaction_id:
                    filtered_corporate_credit_card_expense_groups = _group_expenses(
                        ccc_expenses_without_bank_transaction_id, corporate_credit_card_expense_group_field, workspace_id
                    )

                if ccc_expenses_with_bank_transaction_id:
                    split_expense_group_fields = [
                        field for field in corporate_credit_card_expense_group_field
                        if field not in ('expense_id', 'expense_number')
                    ]
                    split_expense_group_fields.append('bank_transaction_id')

                    groups_with_bank_transaction_id = _group_expenses(
                        ccc_expenses_with_bank_transaction_id, split_expense_group_fields, workspace_id
                    )
                    filtered_corporate_credit_card_expense_groups.extend(groups_with_bank_transaction_id)

            else:
                filtered_corporate_credit_card_expense_groups = _group_expenses(
                    corporate_credit_card_expenses, corporate_credit_card_expense_group_field, workspace_id)

        if configuration.corporate_credit_card_expenses_object == "BILL":
            filtered_corporate_credit_card_expense_groups, corporate_credit_card_skipped_expense_ids = filter_expense_groups(
                filtered_corporate_credit_card_expense_groups,
                corporate_credit_card_expenses,
                corporate_credit_card_expense_group_field,
                None,
                configuration.corporate_credit_card_expenses_object
            )
            skipped_expense_ids.extend(corporate_credit_card_skipped_expense_ids)
        
        expense_groups.extend(filtered_corporate_credit_card_expense_groups)

        for expense_group in expense_groups:
            if expense_group_settings.reimbursable_export_date_type == 'last_spent_at' and expense_group['fund_source'] == 'PERSONAL':
                expense_group['last_spent_at'] = Expense.objects.filter(
                    id__in=expense_group['expense_ids']).order_by('-spent_at').first().spent_at

            if expense_group_settings.ccc_export_date_type == 'last_spent_at' and expense_group['fund_source'] == 'CCC':
                expense_group['last_spent_at'] = Expense.objects.filter(
                    id__in=expense_group['expense_ids']).order_by('-spent_at').first().spent_at
            
            employee_name = Expense.objects.filter(
                id__in=expense_group['expense_ids']
            ).first().employee_name

            employee_name = Expense.objects.filter(
                id__in=expense_group['expense_ids']
            ).first().employee_name
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
                description=expense_group,
                employee_name=employee_name
            )
            
            expense_group_object.expenses.add(*expense_ids)

        return skipped_expense_ids

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
        current_time = datetime.now(timezone.utc)

        for existing_reimbursement in existing_reimbursements:
            existing_reimbursement_ids.append(existing_reimbursement.reimbursement_id)
            primary_key_map[existing_reimbursement.reimbursement_id] = {
                'id': existing_reimbursement.id,
                'state': existing_reimbursement.state
            }

        attributes_to_be_created = []
        attributes_to_be_updated = []

        for reimbursement in reimbursements:
            reimbursement['state'] = 'COMPLETE' if reimbursement['is_paid'] else 'PENDING'
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
                            state=reimbursement['state'],
                            updated_at=current_time
                        )
                    )

        if attributes_to_be_created:
            Reimbursement.objects.bulk_create(attributes_to_be_created, batch_size=50)

        if attributes_to_be_updated:
            Reimbursement.objects.bulk_update(attributes_to_be_updated, fields=['state', 'updated_at'], batch_size=50)


    @staticmethod
    def get_last_synced_at(workspace_id: int):
        """
        Get last synced at datetime
        :param workspace_id: Workspace Id
        :return: last_synced_at datetime
        """
        return Reimbursement.objects.filter(
            workspace_id=workspace_id
        ).order_by('-updated_at').first()


class ExpenseFilter(models.Model):
    """
    Reimbursements
    """
    id = models.AutoField(primary_key=True)
    condition = models.CharField(max_length=255, help_text='Condition for the filter')
    operator = models.CharField(max_length=255, choices=EXPENSE_FILTER_OPERATOR, help_text='Operator for the filter')
    values = ArrayField(base_field=models.CharField(max_length=255), null=True, help_text='Values for the operator')
    rank = models.IntegerField(choices=EXPENSE_FILTER_RANK, help_text='Rank for the filter')
    join_by = models.CharField(
        max_length=3,
        null=True,
        choices=EXPENSE_FILTER_JOIN_BY,
        help_text='Used to join the filter (AND/OR)'
    )
    is_custom = models.BooleanField(default=False, help_text='Custom Field or not')
    custom_field_type = models.CharField(
        max_length=255,
        null=True,
        help_text='Custom field type',
        choices=EXPENSE_FILTER_CUSTOM_FIELD_TYPE
    )
    workspace = models.ForeignKey(
        Workspace, 
        on_delete=models.PROTECT,
        help_text='To which workspace these filters belongs to'
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        db_table = 'expense_filters'
