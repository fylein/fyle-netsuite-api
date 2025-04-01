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
from tests.test_fyle.fixtures import data


@pytest.mark.django_db()
def test_create_expense(create_temp_workspace):
    mock_expenes = data['expenses']
    expense_count = len(Expense.objects.filter(org_id='or79Cob97KSh'))
    Expense.create_expense_objects(
        mock_expenes, 1
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
    user = Workspace.objects.get(id=1).user

    ExpenseGroupSettings.update_expense_group_settings(
        payload, 3, user
    )

    settings = ExpenseGroupSettings.objects.last()

    assert settings.expense_state == 'PAYMENT_PROCESSING'
    assert settings.ccc_expense_state == 'PAID'
    assert settings.ccc_export_date_type == 'spent_at'

def test_create_expense_groups_by_report_id_fund_source_spent_at(db):
    expenses = data['expenses_spent_at']

    expense_objects = Expense.create_expense_objects(expenses, 1)

    configuration = Configuration.objects.get(workspace_id=1)
    workspace = Workspace.objects.get(id=1)

    expense_group_setting = ExpenseGroupSettings.objects.get(workspace_id=1)
    expense_group_setting.reimbursable_export_date_type = 'spent_at'
    reimbursable_expense_group_fields = expense_group_setting.reimbursable_expense_group_fields
    reimbursable_expense_group_fields.append('spent_at')
    expense_group_setting.reimbursable_expense_group_fields = reimbursable_expense_group_fields
    expense_group_setting.save()

    assert len(expense_objects) == 3
    
    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, 1)

    expense_group = ExpenseGroup.objects.filter(workspace=workspace).order_by('-created_at').first()

    assert expense_group.expenses.count() == 2


def test_create_expense_groups_by_report_id_fund_source(db):
    expenses = data['expenses']

    expense_objects = Expense.create_expense_objects(expenses, 49)

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


def test_split_expense_grouping_with_no_bank_transaction_id(db, update_config_for_split_expense_grouping):
    '''
    Test for grouping of 2 expenses with no bank transaction id
    '''
    workspace_id = 1

    # Update settings
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    update_config_for_split_expense_grouping(configuration, expense_group_settings)

    # Get reference to expense objects
    expenses = data['ccc_split_expenses'][:2]
    for expense in expenses:
        expense['bank_transaction_id'] = None

    Expense.create_expense_objects(expenses, workspace_id=workspace_id)
    expense_objects = Expense.objects.filter(expense_id__in=[expense['id'] for expense in expenses])

    assert len(expense_objects) == 2, f'Expected 2 expenses, got {len(expense_objects)}'

    # Test for SINGLE_LINE_ITEM split expense grouping
    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, workspace_id)
    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses])
    assert len(groups) == 2, f'Expected 2 groups, got {len(groups)}'
    old_count = len(groups)

    # Test for MULTIPLE_LINE_ITEM split expense grouping
    expense_group_settings.split_expense_grouping = 'MULTIPLE_LINE_ITEM'
    expense_group_settings.save()

    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, workspace_id)
    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses]).distinct()
    assert len(groups) - old_count == 2, f'Expected 2 groups, got {len(groups) - old_count}'


def test_split_expense_grouping_with_same_and_different_ids(db, update_config_for_split_expense_grouping):
    '''
    Test for grouping of 2 expenses with the same bank transaction id,
    and one expense with a different bank transaction id
    '''
    workspace_id = 1

    # Update settings
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    update_config_for_split_expense_grouping(configuration, expense_group_settings)

    # Get reference to expense objects
    expenses = data['ccc_split_expenses'][:3]
    expenses[0]['bank_transaction_id'] = 'sample_1'
    expenses[1]['bank_transaction_id'] = 'sample_1'
    expenses[2]['bank_transaction_id'] = 'sample_2'

    Expense.create_expense_objects(expenses, workspace_id=workspace_id)
    expense_objects = Expense.objects.filter(expense_id__in=[expense['id'] for expense in expenses])

    assert len(expense_objects) == 3, f'Expected 3 expenses, got {len(expense_objects)}'

    # Test for SINGLE_LINE_ITEM split expense grouping
    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, workspace_id)
    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses])
    assert len(groups) == 3, f'Expected 3 groups, got {len(groups)}'
    old_count = len(groups)

    # Test for MULTIPLE_LINE_ITEM split expense grouping
    expense_group_settings.split_expense_grouping = 'MULTIPLE_LINE_ITEM'
    expense_group_settings.save()

    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, workspace_id)
    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses]).distinct()

    assert len(groups) - old_count == 2, f'Expected 2 groups, got {len(groups) - old_count}'


def test_split_expense_grouping_pairs_of_same_ids(db, update_config_for_split_expense_grouping):
    '''
    Test for grouping of 2 pairs of expenses with the same bank transaction ids
    '''
    workspace_id = 1

    # Update settings
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    update_config_for_split_expense_grouping(configuration, expense_group_settings)

    # Get reference to expense objects
    expenses = data['ccc_split_expenses'][:4]
    expenses[0]['bank_transaction_id'] = 'sample_1'
    expenses[1]['bank_transaction_id'] = 'sample_1'
    expenses[2]['bank_transaction_id'] = 'sample_2'
    expenses[3]['bank_transaction_id'] = 'sample_2'

    Expense.create_expense_objects(expenses, workspace_id=workspace_id)
    expense_objects = Expense.objects.filter(expense_id__in=[expense['id'] for expense in expenses])

    assert len(expense_objects) == 4, f'Expected 4 expenses, got {len(expense_objects)}'

    # Test for SINGLE_LINE_ITEM split expense grouping
    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, workspace_id)
    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses])
    assert len(groups) == 4, f'Expected 4 groups, got {len(groups)}'
    old_count = len(groups)

    # Test for MULTIPLE_LINE_ITEM split expense grouping
    expense_group_settings.split_expense_grouping = 'MULTIPLE_LINE_ITEM'
    expense_group_settings.save()

    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, workspace_id)
    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses]).distinct()

    assert len(groups) - old_count== 2, f'Expected 2 groups, got {len(groups) - old_count}'


def test_create_expense_groups_refund_invalid(db):

    configuration = Configuration.objects.get(workspace_id=1)

    configuration.corporate_credit_card_expenses_object = "BILL"
    configuration.save()

    expenses = data["expense_refund_invalid"]
    expense_objects = Expense.create_expense_objects(expenses, 1)
    assert len(expense_objects) == 2
    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, 1)
    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses]).distinct()

    assert len(groups) == 0

def test_create_expense_groups_refund(db):
    expenses = data["expense_refund_valid"]
    expense_objects = Expense.create_expense_objects(expenses, 1)

    assert len(expense_objects) == 2

    configuration = Configuration.objects.get(workspace_id=1)

    configuration.corporate_credit_card_expenses_object = "BILL"
    configuration.save()

    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, 1)

    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses]).first()

    assert groups.expenses.count() == 2


def creat_expense_groups_by_report_id_refund_spent_at(db):
    workspace = workspace = Workspace.objects.get(id=1)
    configuration = Configuration.objects.get(workspace_id=1)

    configuration.corporate_credit_card_expenses_object = "BILL"
    configuration.save()

    expenses = data["expense_refund_spend_at"]

    expense_objects = Expense.create_expense_objects(expenses, 1)
    expense_group_setting = ExpenseGroupSettings.objects.get(workspace_id=1)
    expense_group_setting.ccc_export_date_type = "spent_at"
    corporate_expense_group_fields = (
        expense_group_setting.corporate_credit_card_expense_group_fields
    )
    corporate_expense_group_fields.append("spent_at")
    expense_group_setting.corporate_credit_card_expense_group_fields = (
        corporate_expense_group_fields
    )
    expense_group_setting.save()

    assert len(expense_objects) == 2

    ExpenseGroup.create_expense_groups_by_report_id_fund_source(expense_objects, configuration, 1)

    groups = ExpenseGroup.objects.filter(expenses__expense_id__in=[expense['id'] for expense in expenses]).first()
    assert groups.expenses.count() == 1
