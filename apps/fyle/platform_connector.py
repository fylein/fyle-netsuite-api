import json
from typing import List
import logging

from django.conf import settings

from fyle.platform import Platform
from fyle_accounting_mappings.models import ExpenseAttribute

import requests
from apps.fyle.models import Reimbursement, ExpenseGroupSettings

logger = logging.getLogger(__name__)

class FylePlatformConnector:
    """
    Fyle Platform Utility Function
    """
    def __init__(self, refresh_token, workspace_id=None):
        client_id = settings.FYLE_CLIENT_ID
        client_secret = settings.FYLE_CLIENT_SECRET
        token_url = settings.FYLE_TOKEN_URI
        server_url = settings.PLATFORM_SERVER_URL
        self.workspace_id = workspace_id

        self.connection = Platform(
            server_url=server_url,
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

    def sync_tax_groups(self):
        """
        Get Tax Groups From Fyle
        """
        generator = self.connection.v1.admin.tax_groups.list_all(query_params={
            'order': 'id.asc'
        })

        tax_attributes = []

        for response in generator:
            if response.get('data'):
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

    def sync_platform_dimensions(self):
        try:
            self.sync_tax_groups()
        except Exception as exception:
            logger.exception(exception)

