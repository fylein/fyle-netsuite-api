from django.conf import settings
from fyle_integrations_platform_connector import PlatformConnector as PlatformIntegrationsConnector
from fyle_accounting_mappings.models import ExpenseAttribute

from apps.workspaces.models import FyleCredential
from apps.workspaces.models import FyleCredential, Workspace
from .connector import FyleConnector


class FylePlatformConnector:
    """
    This class is responsible for connecting to Fyle Platform and fetching data from Fyle Platform and syncing to db.
    """

    def __init__(self, fyle_credentials: FyleCredential, workspace_id=None):
        """
        Initialize the Platform Integration Connector
        """
        if not fyle_credentials.cluster_domain:
            fyle_credentials = self.__store_cluster_domain(fyle_credentials)

        self.connector = PlatformIntegrationsConnector(
            cluster_domain=fyle_credentials.cluster_domain, token_url=settings.FYLE_TOEKN_URI,
            client_id=settings.FYLE_CLIENT_ID, client_secret=settings.FYLE_CLIENT_SECRET,
            refresh_token=fyle_credentials.refresh_token, workspace_id=workspace_id
        )

        @staticmethod
        def __store_cluster_domain(fyle_credentials: FyleCredential) -> FyleCredential:
            """
            Get or store cluster domain
            """
            fyle_connector = FyleConnector(fyle_credentials.refresh_token)
            cluster_domain = fyle_connector.get_cluster_domain()['cluster_domain']
            fyle_credentials.cluster_domain = cluster_domain
            fyle_credentials.save()

            return fyle_credentials


    def sync_tax_groups(self):
        """
        Get Tax Groups From Fyle
        """
        generator = self.connector.tax_groups.get_all_generator()

        tax_attributes = []

        for response in generator:
            for tax_group in response['data']:
                tax_attributes.append({
                    'attribute_type': 'TAX_GROUP',
                    'display_name': 'Tax Group',
                    'value': tax_group['name'],
                    'source_id': tax_group['id'],
                    'detail': {
                        'tax_rate': tax_group['percentage']
                    }
                })

        ExpenseAttribute.bulk_create_or_update_expense_attributes(
            tax_attributes, 'TAX_GROUP', self.workspace_id)
