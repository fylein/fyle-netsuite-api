import pytest
from apps.fyle.models import Reimbursement

from apps.workspaces.models import FyleCredential
from apps.fyle.connector import FyleConnector
from fyle_accounting_mappings.models import ExpenseAttribute


@pytest.mark.django_db()
def test_get_of_expenses(add_fyle_credentials):

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    personal_expenses = fyle_connector.get_expenses(['PAYMENT_PROCESSING'], ['PERSONAL'])
    ccc_expenses = fyle_connector.get_expenses(['PAYMENT_PROCESSING'], ['CCC'])

    assert len(personal_expenses) == 4
    assert len(ccc_expenses) == 2

@pytest.mark.django_db()
def test_sync_reimbursements(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    reimbursements = fyle_connector.sync_reimbursements()

    response = Reimbursement.objects.all()
    assert len(response) == 14

@pytest.mark.django_db()
def test_get_cluster_domain(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    cluster_domain = fyle_connector.get_cluster_domain()

    assert cluster_domain == {'cluster_domain': 'https://staging.fyle.tech'}


@pytest.mark.django_db()
def test_get_employee_profile(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    employee_profile = fyle_connector.get_employee_profile()
    assert employee_profile['employee_email'] == 'admin1@fylefornt.com'
    assert employee_profile['org_name'] == 'Fyle For NetSuite Testing'

@pytest.mark.django_db()
def test_sync(add_fyle_credentials):

    employees = ExpenseAttribute.objects.filter(attribute_type='EMPLOYEE', workspace_id=1)
    projects = ExpenseAttribute.objects.filter(attribute_type='PROJECT', workspace_id=1)
    categories = ExpenseAttribute.objects.filter(attribute_type='CATEGORY', workspace_id=1)

    assert len(employees) == 30
    assert len(projects) == 1193
    assert len(categories) == 341
