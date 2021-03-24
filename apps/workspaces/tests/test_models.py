from datetime import datetime

from django.utils import timezone
from django_q.models import Schedule
from rest_framework.test import APITestCase, APIClient

from apps.workspaces.models import WorkspaceGeneralSettings, WorkspaceSchedule, NetSuiteCredentials
from fyle_netsuite_api.test_utils import TestUtils


class WorkspaceTestModels(APITestCase):

    def setUp(self):
        self.connection = TestUtils.test_connection(self)
        self.access_token = self.connection.access_token

        self.client = APIClient()
        auth = TestUtils.api_authentication(self)

        self.workspace = auth

        self.netsuite_credentials = NetSuiteCredentials.objects.create(
            ns_account_id='ACCOUNT_ID',
            ns_consumer_key='CONSUMER_KEY',
            ns_consumer_secret='CONSUMER_SECRET',
            ns_token_id='TOKEN_KEY',
            ns_token_secret='TOKEN_SECRET',
            workspace_id=self.workspace.id
        )

        self.schedule = Schedule.objects.create(
            func='apps.workspaces.tasks.run_sync_schedule',
            args='test',
            schedule_type=Schedule.MINUTES,
            minutes=1,
            next_run=datetime.now(tz=timezone.utc)
        )

        self.workspace_schedule = WorkspaceSchedule.objects.create(
            workspace_id=self.workspace.id,
            enabled=True,
            start_datetime=datetime.now(tz=timezone.utc),
            interval_hours=12,
            schedule=self.schedule
        )

        self.workspace_general_settings = WorkspaceGeneralSettings.objects.create(
            reimbursable_expenses_object='EXPENSE REPORT',
            corporate_credit_card_expenses_object='',
            sync_fyle_to_netsuite_payments=False,
            sync_netsuite_to_fyle_payments=False,
            import_projects=False,
            auto_map_employees=False,
            workspace_id=self.workspace.id
        )

    def test_netsuite_credential_creation(self):
        netsuite_credentials = self.netsuite_credentials
        self.assertEqual(netsuite_credentials.ns_account_id, 'ACCOUNT_ID', msg='Create NetSuite Credentials Failed')
        self.assertEqual(netsuite_credentials.workspace_id, self.workspace.id, msg='Create NetSuite Credentials Failed')

    def test_create_workspace_schedule_creation(self):
        workspace_schedule = self.workspace_schedule
        self.assertEqual(workspace_schedule.enabled, True, msg='Create Workspace Schedule Failed')
        self.assertEqual(workspace_schedule.schedule, self.schedule, msg='Create Workspace Schedule Failed')

    def test_create_workspace_general_settings(self):
        workspace_general_settings = self.workspace_general_settings
        self.assertEqual(workspace_general_settings.sync_fyle_to_netsuite_payments,
                         False, msg='Create Workspace General Settings Failed')
        self.assertEqual(workspace_general_settings.corporate_credit_card_expenses_object, '',
                         msg='Create Workspace General Settings Failed')


