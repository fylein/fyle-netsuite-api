from fyle_integrations_platform_connector import PlatformConnector
import pytest
from apps.fyle.models import Reimbursement, Expense
from apps.fyle.helpers import get_fyle_orgs, get_cluster_domain

from apps.workspaces.models import FyleCredential
from apps.fyle.connector import FyleConnector

from fyle_accounting_mappings.models import ExpenseAttribute
from .fixtures import data


@pytest.mark.django_db()
def test_get_fyle_orgs(add_fyle_credentials):
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)

    fyle_orgs = get_fyle_orgs(fyle_credentials.refresh_token, 'https://staging.fyle.tech')
    assert fyle_orgs == data['fyle_orgs']


@pytest.mark.django_db()
def test_get_attachments(add_fyle_credentials):

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token)

    attachment = fyle_connector.get_attachment(1)
    assert attachment==None   #later will create an expense with attachments
