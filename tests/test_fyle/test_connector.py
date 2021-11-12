import pytest

from apps.workspaces.models import FyleCredential
from apps.fyle.connector import FyleConnector
from fyle_accounting_mappings.models import ExpenseAttribute


@pytest.mark.django_db()
def test_get_of_expenses(test_connection, create_expense_group):

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    personal_expenses = fyle_connector.get_expenses(['PAYMENT_PROCESSING'], [], ['PERSONAL'])
    ccc_expenses = fyle_connector.get_expenses(['PAYMENT_PROCESSING'], [], ['CCC'])

    assert len(personal_expenses) == 6
    assert len(ccc_expenses) == 6

@pytest.mark.django_db()
def test_sync_l(test_connection, sync_fyle_dimensions):

    employees = ExpenseAttribute.objects.filter(attribute_type='EMPLOYEE')
    projects = ExpenseAttribute.objects.filter(attribute_type='PROJECT')
    categories = ExpenseAttribute.objects.filter(attribute_type='CATEGORY')

    assert len(employees) == 13
    assert len(projects) == 1098
    assert len(categories) == 33
