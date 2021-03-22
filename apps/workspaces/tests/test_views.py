import os
from datetime import datetime

from django.urls import reverse
from django.utils import timezone
from django_q.models import Schedule
from rest_framework.test import APITestCase, APIClient

from apps.workspaces.models import WorkspaceGeneralSettings, WorkspaceSchedule, NetSuiteCredentials
from fyle_netsuite_api.test_utils import TestUtils


class WorkspaceTests(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

        NetSuiteCredentials.objects.create(
            ns_account_id='ACCOUNT_ID',
            ns_consumer_key='CONSUMER_KEY',
            ns_consumer_secret='CONSUMER_SECRET',
            ns_token_id='TOKEN_KEY',
            ns_token_secret='TOKEN_SECRET',
            workspace_id=self.workspace.id
        )

        schedule = Schedule.objects.create(
            func='apps.workspaces.tasks.run_sync_schedule',
            args='test',
            schedule_type=Schedule.MINUTES,
            minutes=1,
            next_run=datetime.now(tz=timezone.utc)
        )

        WorkspaceSchedule.objects.create(
            workspace_id=self.workspace.id,
            enabled=True,
            start_datetime=datetime.now(tz=timezone.utc),
            interval_hours=12,
            schedule=schedule
        )

        WorkspaceGeneralSettings.objects.create(
            reimbursable_expenses_object='EXPENSE REPORT',
            corporate_credit_card_expenses_object='',
            sync_fyle_to_netsuite_payments=False,
            sync_netsuite_to_fyle_payments=False,
            import_projects=False,
            auto_map_employees=False,
            workspace_id=self.workspace.id
        )

        self.workspace_general_settings_payload = {
            'reimbursable_expenses_object': 'EXPENSE REPORT',
            'corporate_credit_card_expenses_object': 'BILL',
            'sync_fyle_to_netsuite_payments': False,
            'sync_netsuite_to_fyle_payments': False,
            'import_projects': False,
            'import_categories': False,
            'auto_map_employees': False,
            'auto_create_destination_entity': False
        }

        self.valid_netsuite_credentials_payload = {
            'workspace': self.workspace,
            'ns_account_id': os.environ.get('ACCOUNT_ID'),
            'ns_token_id': os.environ.get('TOKEN_ID'),
            'ns_token_secret': os.environ.get('TOKEN_SECRET')
        }

        self.invalid_netsuite_credentials_payload = {
            'workspace': self.workspace,
            'ns_account_id': 'NSACC_ID',
            'ns_token_id': 'NSTKN_ID',
            'ns_token_secret': 'NSTKN_SEC'
        }

    def test_get_workspace_detail(self):
        response = self.client.get(reverse('workspace-by-id', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Workspace Failed')

    def test_get_worksace_schedule(self):
        response = self.client.get(reverse('workspace-schedule', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Workspace Schedule Failed')

    def test_get_worksace_general_settings(self):
        response = self.client.get(reverse('workspace-general-settings', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Workspace General Settings Failed')

    def test_get_fyle_credentials(self):
        response = self.client.get(reverse('fyle-credentials', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Fyle Credentials Failed')

    def test_get_netsuite_credentials(self):
        response = self.client.get(reverse('netsuite-credentials', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET NetSuite Credentials Failed')

    def test_create_workspace_general_settings(self):
        response = self.client.post(
            reverse('workspace-general-settings', kwargs={'workspace_id': self.workspace.id}),
            headers={'Authorization': 'Bearer {}'.format(self.access_token)},
            data=self.workspace_general_settings_payload,
            format='json'
        )
        self.assertEqual(response.status_code, 200, msg='GET Workspace General Settings Failed')

    def test_create_valid_netsuite_connection(self):
        response = self.client.post(
            reverse('netsuite-connection', kwargs={'workspace_id': self.workspace.id}),
            headers={'Authorization': 'Bearer {}'.format(self.access_token)},
            data=self.valid_netsuite_credentials_payload
        )
        self.assertEqual(response.status_code, 200, msg='POST NetSuite Credentials Failed')

    def test_create_invalid_netsuite_connection(self):
        response = self.client.post(
            reverse('netsuite-connection', kwargs={'workspace_id': self.workspace.id}),
            headers={'Authorization': 'Bearer {}'.format(self.access_token)},
            data=self.invalid_netsuite_credentials_payload
        )
        self.assertEqual(response.status_code, 400, msg='POST NetSuite Credentials Failed')

