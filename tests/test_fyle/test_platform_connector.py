from fyle_accounting_mappings.models import ExpenseAttribute
import pytest
from apps.workspaces.models import FyleCredential, Workspace
from fyle_integrations_platform_connector import PlatformConnector

@pytest.mark.django_db()
def test_sync_tax_groups(add_fyle_credentials, test_connection):

    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=1)

    fyle_platform_connection = PlatformConnector(
        fyle_credentials=fyle_credentials,
    )
    
    fyle_platform_connection.tax_groups.sync()

    tax_group = ExpenseAttribute.objects.get(attribute_type='TAX_GROUP', value='Netsuite Test Group')

    assert tax_group.value == 'Netsuite Test Group'
    assert tax_group.attribute_type == 'TAX_GROUP'
    assert tax_group.detail == {'tax_rate': 0.28}
