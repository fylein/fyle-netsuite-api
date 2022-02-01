from fyle_integrations_platform_connector import PlatformConnector
import pytest
from apps.fyle.models import ExpenseGroupSettings, Reimbursement, Expense

from apps.workspaces.models import FyleCredential
from apps.fyle.connector import FyleConnector

from fyle_accounting_mappings.models import ExpenseAttribute
from .fixtures import data


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
def test_get_attachments(add_fyle_credentials):

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, 1)

    attachment = fyle_connector.get_attachment('tx3asPlm9wyF')
    assert attachment['filename'] == 'Accidentals.pdf'
