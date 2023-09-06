import json
from urllib import response
from unittest import mock
from django.urls import reverse
import pytest
from apps.fyle.models import Expense, ExpenseGroup, Reimbursement, get_default_expense_group_fields, get_default_expense_state, \
    ExpenseGroupSettings, _group_expenses, get_default_ccc_expense_state
from apps.workspaces.models import Configuration, Workspace
from apps.tasks.models import TaskLog
from apps.fyle.tasks import create_expense_groups
from .fixtures import data


@pytest.mark.django_db()
def test_create_expense(create_temp_workspace):
    mock_expenes = data['expenses']
    expense_count = len(Expense.objects.filter(org_id='or79Cob97KSh'))
    Expense.create_expense_objects(
        mock_expenes
    )

    expense = Expense.objects.filter(org_id='or79Cob97KSh').order_by('created_at')
    assert len(expense) == expense_count+2

    expense = expense.last()
    assert expense.employee_email == 'jhonsnow@fyle.in'
    assert expense.currency == 'USD'
    assert expense.fund_source == 'PERSONAL'


def test_default_fields():
    expense_group_field = get_default_expense_group_fields()
    expense_state = get_default_expense_state()
    ccc_expense_state = get_default_ccc_expense_state()

    assert expense_group_field == ['employee_email', 'report_id', 'claim_number', 'fund_source']
    assert expense_state == 'PAYMENT_PROCESSING'
    assert ccc_expense_state == 'PAID'


@pytest.mark.django_db
def test_expense_group_settings(create_temp_workspace):
    payload = data['expense_group_setting_payload']

    ExpenseGroupSettings.update_expense_group_settings(
        payload, 3
    )

    settings = ExpenseGroupSettings.objects.last()

    assert settings.expense_state == 'PAYMENT_PROCESSING'
    assert settings.ccc_expense_state == 'PAID'
    assert settings.ccc_export_date_type == 'spent_at'

def test_create_expense_groups_by_report_id_fund_source_spent_at(db):
    expenses = data['expenses_spent_at']

    expense_objects = Expense.create_expense_objects(expenses)

    configuration = Configuration.objects.get(workspace_id=1)
    workspace = Workspace.objects.get(id=1)

    expense_group_setting = ExpenseGroupSettings.objects.get(workspace_id=1)
    expense_group_setting.reimbursable_export_date_type = 'spent_at'
    reimbursable_expense_group_fields = expense_group_setting.reimbursable_expense_group_fields
    reimbursable_expense_group_fields.append('spent_at')
    expense_group_setting.reimbursable_expense_group_fields = reimbursable_expense_group_fields
    expense_group_setting.save()

    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, 1)

    expense_group = ExpenseGroup.objects.filter(workspace=workspace).order_by('-created_at').first()

    assert expense_group.expenses.count() == 2


def test_create_expense_groups_by_report_id_fund_source(db):
    expenses = data['expenses']

    expense_objects = Expense.create_expense_objects(expenses)

    configuration = Configuration.objects.get(workspace_id=49)
    workspace = Workspace.objects.get(id=1)

    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, 49)

    expense_groups = ExpenseGroup.objects.filter(workspace=workspace)

    assert len(expense_groups) == 2

    expense_group_setting = ExpenseGroupSettings.objects.get(workspace_id=49)
    corporate_credit_card_expense_group_fields = expense_group_setting.corporate_credit_card_expense_group_fields
    corporate_credit_card_expense_group_fields.append('dummy')
    expense_group_setting.corporate_credit_card_expense_group_fields = corporate_credit_card_expense_group_fields
    expense_group_setting.save()

    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, 49)

    expense_groups = ExpenseGroup.objects.filter(workspace=workspace)

    assert len(expense_groups) == 2


def test_create_reimbursement(db):

    reimbursements = data['reimbursements']

    Reimbursement.create_or_update_reimbursement_objects(reimbursements=reimbursements, workspace_id=1)

    pending_reimbursement = Reimbursement.objects.get(reimbursement_id='reimgCW1Og0BcM')

    pending_reimbursement.state = 'PENDING'
    pending_reimbursement.settlement_id= 'setgCxsr2vTmZ'

    reimbursements[0]['is_paid'] = True

    Reimbursement.create_or_update_reimbursement_objects(reimbursements=reimbursements, workspace_id=1)

    paid_reimbursement = Reimbursement.objects.get(reimbursement_id='reimgCW1Og0BcM')
    paid_reimbursement.state == 'PAID'


def test_get_last_synced_at(db):

    reimbursement = Reimbursement.get_last_synced_at(1)

    assert reimbursement.workspace_id == 1
    assert reimbursement.settlement_id == 'setqi0eM6HUgZ'
    assert reimbursement.state == 'COMPLETE'
