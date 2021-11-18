from fyle_accounting_mappings.models import ExpenseAttribute
import pytest
from apps.workspaces.models import FyleCredential, Workspace
from apps.fyle.platform_connector import FylePlatformConnector

@pytest.mark.django_db()
def test_sync_tax_groups(add_fyle_credentials, test_connection):

    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=1)

    fyle_platform_connection = FylePlatformConnector(
        refresh_token=fyle_credentials.refresh_token,
        workspace_id=1
    )
    
    fyle_platform_connection.sync_tax_groups()

    tax_group = ExpenseAttribute.objects.get(attribute_type='TAX_GROUP', value='Netsuite Test Group')

    assert tax_group.value == 'Netsuite Test Group'
    assert tax_group.attribute_type == 'TAX_GROUP'
    assert tax_group.detail == {'tax_rate': 0.28}

@pytest.mark.django_db()
def test_get_or_store_cluster_domain(add_fyle_credentials):
    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=1)

    fyle_platform_connection = FylePlatformConnector(
        refresh_token=fyle_credentials.refresh_token,
        workspace_id=1
    )

    cluster_domain = fyle_platform_connection.get_or_store_cluster_domain()

    workspace = Workspace.objects.get(id=1)
    assert cluster_domain == workspace.cluster_domain