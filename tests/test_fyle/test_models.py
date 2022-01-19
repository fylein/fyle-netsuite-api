import pytest
from apps.fyle.models import Expense, get_default_expense_group_fields, get_default_expense_state, \
    ExpenseGroupSettings
from .fixtures import data


@pytest.mark.django_db()
def test_create_expense(create_temp_workspace):
    mock_expenes = data['expenses']
    Expense.create_expense_objects(
        mock_expenes, 1
    )

    expense = Expense.objects.filter(org_id='orf6t6jWUnpx')
    assert len(expense) == 5

    expense = expense.last()
    assert expense.employee_email == 'admin1@fylefornt.com'
    assert expense.currency == 'USD'
    assert expense.fund_source == 'PERSONAL'


def test_default_fields():
    expense_group_field = get_default_expense_group_fields()
    expense_state = get_default_expense_state()

    assert expense_group_field == ['employee_email', 'report_id', 'claim_number', 'fund_source']
    assert expense_state == 'PAYMENT_PROCESSING'


@pytest.mark.django_db
def test_expense_group_settings(create_temp_workspace):
    payload = data['expense_group_setting_payload']

    ExpenseGroupSettings.update_expense_group_settings(
        payload, 3
    )

    settings = ExpenseGroupSettings.objects.last()

    assert settings.expense_state == 'PAYMENT_PROCESSING'
    assert settings.ccc_export_date_type == 'current_date'
