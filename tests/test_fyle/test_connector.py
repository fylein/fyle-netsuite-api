import pytest
from apps.fyle.models import Reimbursement

from apps.workspaces.models import FyleCredential
from apps.fyle.connector import FyleConnector
from fyle_accounting_mappings.models import ExpenseAttribute
from .fixtures import data


@pytest.mark.django_db()
def test_get_of_expenses(add_fyle_credentials):

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    personal_expenses = fyle_connector.get_expenses(
        state=['PAYMENT_PROCESSING'], settled_at=[], updated_at=[], fund_source=['PERSONAL'])
    ccc_expenses = fyle_connector.get_expenses(
        state=['PAYMENT_PROCESSING'], settled_at=[], updated_at=[], fund_source=['CCC'])

    assert len(personal_expenses) == 4
    assert len(ccc_expenses) == 2

@pytest.mark.django_db()
def test_sync_reimbursements(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    fyle_connector.sync_reimbursements()

    response = Reimbursement.objects.all()
    assert len(response) == 14

@pytest.mark.django_db()
def test_expense_db_count(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    employee_count = fyle_connector.existing_db_count('EMPLOYEE')
    assert employee_count == 30
    category_count = fyle_connector.existing_db_count('CATEGORY')
    assert category_count == 341

@pytest.mark.django_db()
def test_get_fyle_orgs(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    fyle_orgs = fyle_connector.get_fyle_orgs('https://staging.fyle.tech')
    assert fyle_orgs == data['fyle_orgs']


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

@pytest.mark.django_db()
def test_get_attachments(add_fyle_credentials):

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    attachment = fyle_connector.get_attachment(1)
    assert attachment==None   #later will create an expense with attachments

@pytest.mark.django_db()
def test_sync_employees(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    employees_count = ExpenseAttribute.objects.filter(attribute_type='EMPLOYEE').count()
    assert employees_count == 45

    fyle_connector.sync_employees()

    new_employees_count = ExpenseAttribute.objects.filter(attribute_type='EMPLOYEE').count()

    assert new_employees_count == 46

@pytest.mark.django_db()
def test_sync_categories(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    category_count = ExpenseAttribute.objects.filter(attribute_type='CATEGORY').count()
    assert category_count == 676

    fyle_connector.sync_categories()

    new_category_count = ExpenseAttribute.objects.filter(attribute_type='CATEGORY').count()
    assert new_category_count == 677


@pytest.mark.django_db()
def test_sync_projects(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    project_count = ExpenseAttribute.objects.filter(attribute_type='PROJECT').count()
    assert project_count == 2375

    fyle_connector.sync_projects()

    new_project_count = ExpenseAttribute.objects.filter(attribute_type='PROJECT').count()
    assert new_project_count == 2376


@pytest.mark.django_db()
def test_sync_cost_centers(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    project_count = ExpenseAttribute.objects.filter(attribute_type='COST_CENTER').count()
    assert project_count == 20

    fyle_connector.sync_cost_centers()

    new_project_count = ExpenseAttribute.objects.filter(attribute_type='COST_CENTER').count()
    assert new_project_count == 25

@pytest.mark.django_db()
def test_sync_expense_custom_fields(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    fyle_connector.sync_expense_custom_fields()

    expense_field = ExpenseAttribute.objects.filter(attribute_type='TEST_CUSTOM_FIELD').count()
    assert expense_field == 1
