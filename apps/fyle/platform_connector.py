from django.conf import settings
import logging
from django.conf import settings
from fyle_integrations_platform_connector import PlatformConnector

from apps.workspaces.models import FyleCredential
from .connector import FyleConnector

logger = logging.getLogger(__name__)

class FylePlatformConnector:
    """
    This class is responsible for connecting to Fyle Platform and fetching data from Fyle Platform and syncing to db.
    """

    def __init__(self, fyle_credentials: FyleCredential, workspace_id=None):
        """
        Initialize the Platform Integration connector
        """
        print(fyle_credentials.cluster_domain)
        if not fyle_credentials.cluster_domain:
            fyle_credentials = self.__store_cluster_domain(fyle_credentials)

        self.connector = PlatformConnector(fyle_credentials)


    @staticmethod
    def __store_cluster_domain(fyle_credentials: FyleCredential) -> FyleCredential:
        """
        Get or store cluster domain.
        """
        fyle_connector = FyleConnector(fyle_credentials.refresh_token, workspace_id=fyle_credentials.workspace_id)
        cluster_domain = fyle_connector.get_cluster_domain()['cluster_domain']
        fyle_credentials.cluster_domain = cluster_domain
        fyle_credentials.save()

        return fyle_credentials
