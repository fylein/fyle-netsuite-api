import pytest
from fyle_integrations_platform_connector import PlatformConnector
from fyle_accounting_mappings.models import ExpenseAttribute

from apps.workspaces.models import FyleCredential, Workspace
from .fixtures import data

@pytest.mark.django_db()
def test_sync_tax_groups(access_token, mocker, db):
    mocker.patch(
      'fyle.platform.apis.v1beta.admin.TaxGroups.list_all',
      return_value=data['get_all_tax_groups']
   )
    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=1)

    fyle_platform_connection = PlatformConnector(
        fyle_credentials=fyle_credentials,
    )
    
    fyle_platform_connection.tax_groups.sync()

    tax_group = ExpenseAttribute.objects.get(attribute_type='TAX_GROUP', value='GST')

    assert tax_group.value == 'GST'
    assert tax_group.attribute_type == 'TAX_GROUP'
    assert tax_group.detail == {'tax_rate': 0.18}
