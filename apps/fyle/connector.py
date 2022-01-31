from typing import List
import json
import logging
from datetime import datetime

from django.conf import settings

from fylesdk import FyleSDK, UnauthorizedClientError, NotFoundClientError, InternalServerError, WrongParamsError

from fyle_accounting_mappings.models import ExpenseAttribute

import requests

from apps.fyle.models import Reimbursement, ExpenseGroupSettings

logger = logging.getLogger(__name__)


class FyleConnector:
    """
    Fyle utility functions
    """

    def __init__(self, refresh_token, workspace_id=None):
        client_id = settings.FYLE_CLIENT_ID
        client_secret = settings.FYLE_CLIENT_SECRET
        base_url = settings.FYLE_BASE_URL
        self.workspace_id = workspace_id

        self.connection = FyleSDK(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

 
    def get_attachment(self, expense_id: str):
        """
        Get attachments against expense_ids
        """
        attachment = self.connection.Expenses.get_attachments(expense_id)

        if attachment['data']:
            attachment = attachment['data'][0]
            attachment_format = attachment['filename'].split('.')[-1]
            if attachment_format != 'html':
                attachment['expense_id'] = expense_id
                return attachment
            else:
                return []

    def post_reimbursement(self, reimbursement_ids: list):
        """
        Process Reimbursements in bulk.
        """
        return self.connection.Reimbursements.post(reimbursement_ids)
