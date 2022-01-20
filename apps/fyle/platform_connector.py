import json
from typing import List
import logging

from django.conf import settings

from fyle.platform import Platform
from fyle_accounting_mappings.models import ExpenseAttribute

import requests
from apps.fyle.models import Reimbursement, ExpenseGroupSettings
from apps.workspaces.models import FyleCredential, Workspace
from .connector import FyleConnector

logger = logging.getLogger(__name__)

class FylePlatformConnector:
    """
    Fyle Platform Utility Function
    """

    def __init__(self, refresh_token, workspace_id=None):
        self.workspace_id = workspace_id
        cluster_domain = self.get_or_store_cluster_domain()

        client_id = settings.FYLE_CLIENT_ID
        client_secret = settings.FYLE_CLIENT_SECRET
        token_url = settings.FYLE_TOKEN_URI
        server_url = '{}/platform/v1beta'.format(cluster_domain)

        self.connection = Platform(
            server_url=server_url,
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

    def get_or_store_cluster_domain(self):
        workspace = Workspace.objects.filter(pk=self.workspace_id).first()
        if workspace.cluster_domain:
            return workspace.cluster_domain
        else:
            fyle_credentials = FyleCredential.objects.get(workspace_id=self.workspace_id)
            fyle_connector = FyleConnector(fyle_credentials.refresh_token, self.workspace_id)

            cluster_domain = fyle_connector.get_cluster_domain()['cluster_domain']
            workspace.cluster_domain = cluster_domain
            workspace.save()

            return cluster_domain

    def sync_tax_groups(self):
        """
        Get Tax Groups From Fyle
        """
        generator = self.connection.v1beta.admin.tax_groups.list_all(query_params={
            'order': 'id.asc'
        })

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
