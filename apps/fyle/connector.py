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

    def _post_request(self, url, body):
        """
        Create a HTTP post request.
        """

        access_token = self.connection.access_token
        api_headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer {0}'.format(access_token)
        }

        response = requests.post(
            url,
            headers=api_headers,
            data=body
        )

        if response.status_code == 200:
            return json.loads(response.text)

        elif response.status_code == 401:
            raise UnauthorizedClientError('Wrong client secret or/and refresh token', response.text)

        elif response.status_code == 404:
            raise NotFoundClientError('Client ID doesn\'t exist', response.text)

        elif response.status_code == 400:
            raise WrongParamsError('Some of the parameters were wrong', response.text)

        elif response.status_code == 500:
            raise InternalServerError('Internal server error', response.text)

    def _get_request(self, url, params):
        """
        Create a HTTP get request.
        """

        access_token = self.connection.access_token
        api_headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer {0}'.format(access_token)
        }
        api_params = {}

        for k in params:
            # ignore all unused params
            if not params[k] is None:
                p = params[k]

                # convert boolean to lowercase string
                if isinstance(p, bool):
                    p = str(p).lower()

                api_params[k] = p

        response = requests.get(
            url,
            headers=api_headers,
            params=api_params
        )

        if response.status_code == 200:
            return json.loads(response.text)

        elif response.status_code == 401:
            raise UnauthorizedClientError('Wrong client secret or/and refresh token', response.text)

        elif response.status_code == 404:
            raise NotFoundClientError('Client ID doesn\'t exist', response.text)

        elif response.status_code == 400:
            raise WrongParamsError('Some of the parameters were wrong', response.text)

        elif response.status_code == 500:
            raise InternalServerError('Internal server error', response.text)

    def __format_updated_at(self, updated_at):
        return 'gte:{0}'.format(datetime.strftime(updated_at, '%Y-%m-%dT%H:%M:%S.000Z'))

    def __get_last_synced_at(self, attribute_type: str):
        latest_synced_record = ExpenseAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type=attribute_type
        ).order_by('-updated_at').first()
        updated_at = self.__format_updated_at(latest_synced_record.updated_at) if latest_synced_record else None

        return updated_at

    def existing_db_count(self, attribute_type: str):
        return ExpenseAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type=attribute_type
        ).count()

    def get_employee_profile(self):
        """
        Get expenses from fyle
        """
        employee_profile = self.connection.Employees.get_my_profile()

        return employee_profile['data']

    def get_cluster_domain(self):
        """
        Get cluster domain name from fyle
        """

        body = {}
        api_url = '{0}/oauth/cluster/'.format(settings.FYLE_BASE_URL)

        return self._post_request(api_url, body)

    def get_fyle_orgs(self, cluster_domain):
        """
        Get fyle orgs of a user
        """

        params = {}
        api_url = '{0}/api/orgs/'.format(cluster_domain)

        return self._get_request(api_url, params)

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
