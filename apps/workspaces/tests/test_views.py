from datetime import datetime

from django.urls import reverse
from django.utils import timezone
from django_q.models import Schedule
from fyle_rest_auth.models import AuthToken, User
from fylesdk import FyleSDK
from rest_framework.test import APITestCase, APIClient

from apps.workspaces.models import Workspace, WorkspaceGeneralSettings, WorkspaceSchedule, NetSuiteCredentials
from fyle_netsuite_api import settings


class WorkspaceTests(APITestCase):

    def setUp(self):
        client_id = settings.FYLE_CLIENT_ID
        client_secret = settings.FYLE_CLIENT_SECRET
        base_url = settings.FYLE_BASE_URL
        refresh_token = settings.FYLE_REFRESH_TOKEN

        self.connection = FyleSDK(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            jobs_url=settings.FYLE_JOBS_URL
        )

        self.access_token = self.connection.access_token

        self.user = User(password='', last_login=datetime.now(tz=timezone.utc), id=1, email='user_email',
                         user_id='user_id', full_name='', active='t', staff='f', admin='t')
        self.user.save()

        self.auth_token = AuthToken(
            id=1,
            refresh_token=refresh_token,
            user=self.user
        )
        self.auth_token.save()

        self.client = APIClient()
        self.api_authentication()

    def api_authentication(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        self.client.post('{0}/workspaces/'.format(settings.API_URL),
                         headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.workspace = Workspace.objects.first()

    def test_get_worksace_schedules(self):
        schedule = Schedule.objects.create(
            func='apps.workspaces.tasks.run_sync_schedule',
            args='test',
            schedule_type=Schedule.MINUTES,
            minutes=77,
            next_run=datetime.now(tz=timezone.utc)
        )
        WorkspaceSchedule.objects.create(
            workspace_id=self.workspace.id,
            enabled=True,
            start_datetime=datetime.now(tz=timezone.utc),
            interval_hours=12,
            schedule=schedule
        )
        response = self.client.get(reverse('workspace-schedule', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Workspace Schedule Failed')

    def test_get_worksace_general_settings(self):
        WorkspaceGeneralSettings.objects.create(
            reimbursable_expenses_object="EXPENSE REPORT",
            corporate_credit_card_expenses_object="",
            sync_fyle_to_netsuite_payments=False,
            sync_netsuite_to_fyle_payments=False,
            import_projects=False,
            auto_map_employees=False,
            workspace_id=self.workspace.id
        )
        response = self.client.get(reverse('workspace-general-settings', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Workspace General Settings Failed')

    def test_get_fyle_credentials(self):
        response = self.client.get(reverse('fyle-credentials', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET Fyle Credentials Failed')

    def test_get_netsuite_credentials(self):
        NetSuiteCredentials.objects.create(
            ns_account_id='ACCOUNT_ID',
            ns_consumer_key='CONSUMER_KEY',
            ns_consumer_secret='CONSUMER_SECRET',
            ns_token_id='TOKEN_KEY',
            ns_token_secret='TOKEN_SECRET',
            workspace_id=self.workspace.id
        )
        response = self.client.get(reverse('netsuite-credentials', kwargs={'workspace_id': self.workspace.id}),
                                   headers={'Authorization': 'Bearer {}'.format(self.access_token)})
        self.assertEqual(response.status_code, 200, msg='GET NetSuite Credentials Failed')

    def test_create_workspace_general_settings(self):
        response = self.client.post(
            reverse('workspace-general-settings', kwargs={'workspace_id': self.workspace.id}),
            headers={'Authorization': 'Bearer {}'.format(self.access_token)},
            data={
                "reimbursable_expenses_object": "EXPENSE REPORT",
                "corporate_credit_card_expenses_object": "",
                "sync_fyle_to_netsuite_payments": False,
                "sync_netsuite_to_fyle_payments": False,
                "import_projects": False,
                "auto_map_employees": False
            },
            format='json'
        )
        self.assertEqual(response.status_code, 200, msg='GET Workspace General Settings Failed')
