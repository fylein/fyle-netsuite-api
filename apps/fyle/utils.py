from typing import List
import json
import logging

from django.conf import settings

from fylesdk import FyleSDK, UnauthorizedClientError, NotFoundClientError, InternalServerError, WrongParamsError

from fyle_accounting_mappings.models import ExpenseAttribute

import requests

from apps.fyle.models import Reimbursement

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
            refresh_token=refresh_token,
            jobs_url=settings.FYLE_JOBS_URL
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

    def get_expenses(self, state: List[str], updated_at: List[str], fund_source: List[str]):
        """
        Get expenses from fyle
        """
        expenses = self.connection.Expenses.get_all(state=state, updated_at=updated_at, fund_source=fund_source)
        expenses = list(filter(lambda expense: expense['amount'] > 0, expenses))
        expenses = list(
            filter(lambda expense: not (not expense['reimbursable'] and expense['fund_source'] == 'PERSONAL'),
                   expenses))

        return expenses

    def sync_employees(self):
        """
        Get employees from fyle
        """
        employees = self.connection.Employees.get_all()

        employee_attributes = []

        for employee in employees:
            employee_attributes.append({
                'attribute_type': 'EMPLOYEE',
                'display_name': 'Employee',
                'value': employee['employee_email'],
                'source_id': employee['id'],
                'detail': {
                    'user_id': employee['user_id'],
                    'employee_code': employee['employee_code'],
                    'full_name': employee['full_name'],
                    'location': employee['location'],
                    'department': employee['department'],
                    'department_id': employee['department_id'],
                    'department_code': employee['department_code']
                }
            })

        ExpenseAttribute.bulk_create_or_update_expense_attributes(employee_attributes, 'EMPLOYEE', self.workspace_id, True)

        return []

    def sync_categories(self, active_only: bool):
        """
        Get categories from fyle
        """
        categories = self.connection.Categories.get(active_only=active_only)['data']

        category_attributes = []

        for category in categories:
            if category['name'] != category['sub_category']:
                category['name'] = '{0} / {1}'.format(category['name'], category['sub_category'])

            category_attributes.append({
                'attribute_type': 'CATEGORY',
                'display_name': 'Category',
                'value': category['name'],
                'source_id': category['id']
            })

        ExpenseAttribute.bulk_create_or_update_expense_attributes(category_attributes, 'CATEGORY', self.workspace_id)

        return []

    def sync_cost_centers(self, active_only: bool):
        """
        Get cost centers from fyle
        """
        cost_centers = self.connection.CostCenters.get(active_only=active_only)['data']

        cost_center_attributes = []

        for cost_center in cost_centers:
            cost_center_attributes.append({
                'attribute_type': 'COST_CENTER',
                'display_name': 'Cost Center',
                'value': cost_center['name'],
                'source_id': cost_center['id']
            })

        ExpenseAttribute.bulk_create_or_update_expense_attributes(cost_center_attributes, 'COST_CENTER', self.workspace_id)

        return []

    def sync_projects(self):
        """
        Get projects from fyle
        """
        all_projects = []
        limit = 1000
        offset = 0

        while True:
            projects = self.connection.Projects.get(limit=str(limit), offset=str(offset))['data']

            if len(projects) == 0:
                break
            else:
                all_projects.extend(projects)
                offset = offset + limit

        project_attributes = []

        for project in all_projects:
            project_attributes.append({
                'attribute_type': 'PROJECT',
                'display_name': 'Project',
                'value': project['name'],
                'source_id': project['id']
            })

        ExpenseAttribute.bulk_create_or_update_expense_attributes(project_attributes, 'PROJECT', self.workspace_id)

        return []

    def sync_expense_custom_fields(self, active_only: bool):
        """
        Get Expense Custom Fields from Fyle (Type = Select)
        """
        expense_custom_fields = self.connection.ExpensesCustomFields.get(active=active_only)['data']

        expense_custom_fields = filter(lambda field: field['type'] == 'SELECT', expense_custom_fields)

        for custom_field in expense_custom_fields:
            expense_custom_field_attributes = []
            count = 1

            for option in custom_field['options']:
                expense_custom_field_attributes.append({
                    'attribute_type': custom_field['name'].upper().replace(' ', '_'),
                    'display_name': custom_field['name'],
                    'value': option,
                    'source_id': 'expense_custom_field.{}.{}'.format(custom_field['name'].lower(), count)
                })
                count = count + 1

            ExpenseAttribute.bulk_create_or_update_expense_attributes(expense_custom_field_attributes,
                custom_field['name'].upper().replace(' ', '_'), self.workspace_id)

        return []

    def sync_reimbursements(self):
        """
        Get reimbursements from fyle
        """
        reimbursements = self.connection.Reimbursements.get_all()

        Reimbursement.create_or_update_reimbursement_objects(
            reimbursements, self.workspace_id
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


    def sync_dimensions(self):
        try:
            self.sync_employees()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_categories(active_only=False)
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_cost_centers(active_only=False)
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_projects()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_expense_custom_fields(active_only=True)
        except Exception as exception:
            logger.exception(exception)
