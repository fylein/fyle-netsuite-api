from datetime import datetime, timezone
from unittest import mock
import pytest
from rest_framework.test import APIClient
from fyle_rest_auth.models import AuthToken, User
from fyle.platform import Platform

from apps.workspaces.models import NetSuiteCredentials, FyleCredential, Workspace
from apps.fyle.helpers import get_access_token
from fyle_netsuite_api.tests import settings

from .test_fyle.fixtures import data as fyle_data
from apps.fyle.models import Expense, ExpenseGroup


@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture()
def access_token(db):
    """
    Creates a connection with Fyle
    """

    client_id = settings.FYLE_CLIENT_ID
    client_secret = settings.FYLE_CLIENT_SECRET
    token_url = settings.FYLE_TOKEN_URI
    refresh_token = settings.FYLE_REFRESH_TOKEN
    final_access_token = get_access_token(refresh_token=refresh_token)

    fyle = Platform(
        server_url="https://staging.fyle.tech/platform/v1",
        token_url=token_url,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret
    )

    user_profile = fyle.v1.spender.my_profile.get()['data']['user']
    user = User(
        password='', last_login=datetime.now(tz=timezone.utc), id=1, email=user_profile['email'],
        user_id=user_profile['id'], full_name='', active='t', staff='f', admin='t'
    )

    user.save()

    auth_token = AuthToken(
        id=1,
        refresh_token=refresh_token,
        user=user
    )
    auth_token.save()

    return final_access_token

@pytest.fixture(autouse=True)
def add_netsuite_credentials(db):
    from apps.fyle.models import ExpenseGroupSettings
    from apps.workspaces.models import Configuration
    from datetime import datetime, timezone

    workspaces = [1,2,49]
    for workspace_id in workspaces:

        workspace, _ = Workspace.objects.get_or_create(
            id=workspace_id,
            defaults={
                'name': f'Test Workspace {workspace_id}',
                'fyle_org_id': f'or79Cob97KSh{workspace_id}',
                'ns_account_id': settings.NS_ACCOUNT_ID,
                'last_synced_at': None,
                'source_synced_at': None,
                'destination_synced_at': None,
                'created_at': datetime.now(tz=timezone.utc),
                'updated_at': datetime.now(tz=timezone.utc)
            }
        )
        
        ExpenseGroupSettings.objects.get_or_create(
            workspace_id=workspace_id,
            defaults={
                'reimbursable_expense_group_fields': ['employee_email', 'report_id', 'claim_number', 'fund_source'],
                'corporate_credit_card_expense_group_fields': ['fund_source', 'employee_email', 'claim_number', 'expense_id', 'report_id'],
                'expense_state': 'PAYMENT_PROCESSING',
                'import_card_credits': False
            }
        )
        
        from apps.workspaces.models import LastExportDetail
        LastExportDetail.objects.get_or_create(workspace_id=workspace_id)
        
        NetSuiteCredentials.objects.get_or_create(
            workspace_id=workspace_id,
            defaults={
                'ns_account_id': workspace.ns_account_id,
                'ns_consumer_key': settings.NS_CONSUMER_KEY,
                'ns_consumer_secret': settings.NS_CONSUMER_SECRET,
                'ns_token_id': settings.NS_TOKEN_ID,
                'ns_token_secret': settings.NS_TOKEN_SECRET,
            }
        )
        
        Configuration.objects.get_or_create(
            workspace_id=workspace_id,
            defaults={
                'reimbursable_expenses_object': 'EXPENSE REPORT',
                'corporate_credit_card_expenses_object': 'CREDIT CARD CHARGE'
            }
        )

@pytest.fixture(autouse=True)
def add_fyle_credentials(db):
    workspaces = [1,2,49]
    for workspace_id in workspaces:
        FyleCredential.objects.get_or_create(
            workspace_id=workspace_id,
            defaults={
                'refresh_token': settings.FYLE_REFRESH_TOKEN,
                'cluster_domain': 'https://staging.fyle.tech'
            }
        )

@pytest.fixture(scope="session", autouse=True)
def default_session_fixture(request):
    patched_1 = mock.patch(
        'netsuitesdk.internal.client.NetSuiteClient.connect_tba',
        return_value=None
    )
    patched_1.__enter__()

    patched_2 = mock.patch(
        'fyle_rest_auth.authentication.get_fyle_admin',
        return_value=fyle_data['get_my_profile']
    )
    patched_2.__enter__()

    patched_3 = mock.patch(
        'fyle.platform.internals.auth.Auth.update_access_token',
        return_value='asnfalsnkflanskflansfklsan'
    )
    patched_3.__enter__()

    patched_4 = mock.patch(
        'apps.fyle.helpers.post_request',
        return_value={
            'access_token': 'easnfkjo12233.asnfaosnfa.absfjoabsfjk',
            'cluster_domain': 'https://staging.fyle.tech'
        }
    )
    patched_4.__enter__()

    patched_5 = mock.patch(
        'fyle.platform.apis.v1.spender.MyProfile.get',
        return_value=fyle_data['get_my_profile']
    )
    patched_5.__enter__()

    patched_6 = mock.patch(
        'netsuitesdk.internal.client.NetSuiteClient.__init__',
        return_value=None
    )
    patched_6.__enter__()

    patched_7 = mock.patch(
        'netsuitesdk.api.journal_entries.JournalEntries.__init__',
        return_value=None
    )
    patched_7.__enter__()

    patched_8 = mock.patch(
        'apps.workspaces.tasks.send_email',
        return_value=None
    )
    patched_8.__enter__()

@pytest.fixture(autouse=True)
def mock_rabbitmq():
    with mock.patch('apps.fyle.queue.RabbitMQConnection.get_instance') as mock_rabbitmq:
        mock_instance = mock.Mock()
        mock_instance.publish.return_value = None
        mock_instance.connect.return_value = None
        mock_rabbitmq.return_value = mock_instance
        yield mock_rabbitmq



@pytest.fixture
def add_expense_report_data(db):
    """
    Create test data for expense report change tests
    """
    workspace = Workspace.objects.get(id=1)

    # Create test expenses
    expense1 = Expense.objects.create(
        workspace_id=workspace.id,
        expense_id='tx_report_test_1',
        employee_email='test@fyle.in',
        employee_name='Test Employee',
        category='Meals',
        sub_category='Team Meals',
        project='Test Project',
        expense_number='E/2024/01/T/1',
        claim_number='C/2024/01/R/1',
        amount=100.0,
        currency='USD',
        foreign_amount=100.0,
        foreign_currency='USD',
        settlement_id='setl_test_1',
        reimbursable=True,
        billable=False,
        state='APPROVED',
        vendor='Test Vendor',
        cost_center='Test Cost Center',
        purpose='Test meal expense',
        report_id='rp_test_report_1',
        report_title='Test Report 1',
        spent_at='2024-01-01T00:00:00Z',
        approved_at='2024-01-01T00:00:00Z',
        expense_created_at='2024-01-01T00:00:00Z',
        expense_updated_at='2024-01-01T00:00:00Z',
        created_at='2024-01-01T00:00:00Z',
        updated_at='2024-01-01T00:00:00Z',
        fund_source='PERSONAL',
        verified_at='2024-01-01T00:00:00Z',
        custom_properties={},
        org_id=workspace.fyle_org_id,
        file_ids=[],
        accounting_export_summary={}
    )

    expense2 = Expense.objects.create(
        workspace_id=workspace.id,
        expense_id='tx_report_test_2',
        employee_email='test@fyle.in',
        employee_name='Test Employee',
        category='Travel',
        sub_category='Flight',
        project='Test Project',
        expense_number='E/2024/01/T/2',
        claim_number='C/2024/01/R/1',
        amount=200.0,
        currency='USD',
        foreign_amount=200.0,
        foreign_currency='USD',
        settlement_id='setl_test_2',
        reimbursable=True,
        billable=False,
        state='APPROVED',
        vendor='Test Airline',
        cost_center='Test Cost Center',
        purpose='Test travel expense',
        report_id='rp_test_report_1',
        report_title='Test Report 1',
        spent_at='2024-01-01T00:00:00Z',
        approved_at='2024-01-01T00:00:00Z',
        expense_created_at='2024-01-01T00:00:00Z',
        expense_updated_at='2024-01-01T00:00:00Z',
        created_at='2024-01-01T00:00:00Z',
        updated_at='2024-01-01T00:00:00Z',
        fund_source='PERSONAL',
        verified_at='2024-01-01T00:00:00Z',
        custom_properties={},
        org_id=workspace.fyle_org_id,
        file_ids=[],
        accounting_export_summary={}
    )

    # Create non-exported expense group
    expense_group = ExpenseGroup.objects.create(
        workspace_id=workspace.id,
        fund_source='PERSONAL',
        exported_at=None,
        description={
            'report_id': 'rp_test_report_1',
            'employee_email': 'test@fyle.in',
            'claim_number': 'C/2024/01/R/1',
            'fund_source': 'PERSONAL'
        }
    )
    expense_group.expenses.add(expense1, expense2)

    return {
        'workspace': workspace,
        'expenses': [expense1, expense2],
        'expense_group': expense_group
    }
