"""
Fyle Models
"""
from itertools import groupby
from typing import List, Dict

from django.db import models
from django.contrib.postgres.fields import JSONField

from apps.workspaces.models import Workspace


class Expense(models.Model):
    """
    Expense
    """
    id = models.AutoField(primary_key=True)
    employee_email = models.EmailField(max_length=255, unique=False, help_text='Email id of the Fyle employee')
    category = models.CharField(max_length=255, null=True, blank=True, help_text='Fyle Expense Category')
    sub_category = models.CharField(max_length=255, null=True, blank=True, help_text='Fyle Expense Sub-Category')
    project = models.CharField(max_length=255, null=True, blank=True, help_text='Project')
    expense_id = models.CharField(max_length=255, unique=True, help_text='Expense ID')
    expense_number = models.CharField(max_length=255, help_text='Expense Number')
    claim_number = models.CharField(max_length=255, help_text='Claim Number', null=True)
    amount = models.FloatField(help_text='Home Amount')
    currency = models.CharField(max_length=5, help_text='Home Currency')
    foreign_amount = models.FloatField(null=True, help_text='Foreign Amount')
    foreign_currency = models.CharField(null=True, max_length=5, help_text='Foreign Currency')
    settlement_id = models.CharField(max_length=255, help_text='Settlement ID')
    reimbursable = models.BooleanField(default=False, help_text='Expense reimbursable or not')
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

    class Meta:
        db_table = 'expenses'

    @staticmethod
    def create_expense_objects(expenses: List[Dict]):
        """
        Bulk create expense objects
        """
        expense_objects = []

        for expense in expenses:
            expense_object, _ = Expense.objects.update_or_create(
                expense_id=expense['id'],
                defaults={
                    'employee_email': expense['employee_email'],
                    'category': expense['category_name'],
                    'sub_category': expense['sub_category'],
                    'project': expense['project_name'],
                    'expense_number': expense['expense_number'],
                    'claim_number': expense['claim_number'],
                    'amount': expense['amount'],
                    'currency': expense['currency'],
                    'foreign_amount': expense['foreign_amount'],
                    'foreign_currency': expense['foreign_currency'],
                    'settlement_id': expense['settlement_id'],
                    'reimbursable': expense['reimbursable'],
                    'exported': expense['exported'],
                    'state': expense['state'],
                    'vendor': expense['vendor'],
                    'cost_center': expense['cost_center_name'],
                    'purpose': expense['purpose'],
                    'report_id': expense['report_id'],
                    'spent_at': expense['spent_at'],
                    'approved_at': expense['approved_at'],
                    'expense_created_at': expense['created_at'],
                    'expense_updated_at': expense['updated_at'],
                    'fund_source': expense['fund_source']
                }
            )
            expense_objects.append(expense_object)

        return expense_objects


class ExpenseGroup(models.Model):
    """
    Expense Group
    """
    id = models.AutoField(primary_key=True)
    fyle_group_id = models.CharField(max_length=255, unique=True, help_text='fyle expense group id report id, etc')
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT,
                                  help_text='To which workspace this expense group belongs to')
    expenses = models.ManyToManyField(Expense, help_text="Expenses under this Expense Group")
    description = JSONField(max_length=255, help_text='Description', null=True)
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at')

    class Meta:
        unique_together = ('fyle_group_id', 'workspace')
        db_table = 'expense_groups'

    @staticmethod
    def create_expense_groups_by_report_id(expense_objects: List[Expense], workspace_id):
        """
        Group expense by report_id
        """
        expense_groups = groupby(
            expense_objects, lambda expense: (expense.report_id, expense.employee_email, expense.claim_number)
        )

        expense_group_objects = []

        for expense_group, _ in expense_groups:
            report_id = expense_group[0]
            employee_email = expense_group[1]
            claim_number = expense_group[2]

            expense_ids = Expense.objects.filter(report_id=report_id).values_list(
                'id', flat=True
            )

            expense_group_object, _ = ExpenseGroup.objects.update_or_create(
                fyle_group_id=report_id,
                workspace_id=workspace_id,
                defaults={
                    'description': {
                        'employee_email': employee_email,
                        'claim_number': claim_number
                    }
                }
            )

            expense_group_object.expenses.add(*expense_ids)

            expense_group_objects.append(expense_group_object)

        return expense_group_objects
