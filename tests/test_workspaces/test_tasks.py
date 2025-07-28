import pytest
from apps.fyle.models import Expense, ExpenseGroup
from apps.workspaces.models import Configuration, WorkspaceSchedule, FyleCredential, Workspace, LastExportDetail
from apps.workspaces.tasks import *
from tests.test_fyle.fixtures import data as fyle_data


def test_schedule_sync(db):
    schedule_sync(2, True, 3, ['ashwin.t@fyle.in'], ['ashwin.t@fyle.in'], False)

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.interval_hours == 3
    assert ws_schedule.enabled == True

    schedule_sync(2, False, 0, ['ashwin.t@fyle.in'], ['ashwin.t@fyle.in'], False)

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.enabled == False

def test_run_sync_schedule(db, access_token, add_fyle_credentials, add_netsuite_credentials, mocker):
    expense_group_count = ExpenseGroup.objects.filter(workspace_id=1).count()
    expenses_count = Expense.objects.filter(org_id='or79Cob97KSh').count()

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=fyle_data['expenses']
    )
    run_sync_schedule(1)

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.reimbursable_expenses_object = 'BILL'
    configuration.save()
    run_sync_schedule(1)

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.reimbursable_expenses_object = 'JOURNAL ENTRY'
    configuration.save()
    run_sync_schedule(1)

    expense_group = ExpenseGroup.objects.filter(workspace_id=1).count()
    expenses = Expense.objects.filter(org_id='or79Cob97KSh').count()
    assert expense_group == expense_group_count+2
    assert expenses == expenses_count+2

    run_sync_schedule(2)

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.corporate_credit_card_expenses_object = 'JOURNAL ENTRY'
    configuration.save()
    run_sync_schedule(2)

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.corporate_credit_card_expenses_object = 'EXPENSE REPORT'
    configuration.save()
    run_sync_schedule(2)

    expense_group = ExpenseGroup.objects.filter(workspace_id=2).count()
    expenses = Expense.objects.filter(org_id='oraWFQlEpjbb').count()

    assert expense_group == 2
    assert expenses == 2


@pytest.mark.django_db()
def test_delete_cards_mapping_settings():
    configuration = Configuration.objects.get(workspace_id=49)
    configuration.map_fyle_cards_netsuite_account = False
    configuration.save()
    delete_cards_mapping_settings(configuration)


@pytest.mark.django_db()
def test_run_email_notification(db, mocker, create_task_logs):
    
    run_email_notification(49)
    ws_schedule = WorkspaceSchedule.objects.get(
        workspace_id=49
    )
    assert ws_schedule.error_count == 1

    attribute = ExpenseAttribute.objects.filter(workspace_id=49, value='owner@fyleforintacct.in').first()
    attribute.delete()

    ws_schedule = WorkspaceSchedule.objects.get(workspace_id=49)
    ws_schedule.enabled = True
    ws_schedule.emails_selected = ['owner@fyleforintacct.in']
    ws_schedule.additional_email_options = [{'email': 'owner@fyleforintacct.in', 'name': 'Ashwin'}]
    ws_schedule.save()

    run_email_notification(49)

    ws_schedule = WorkspaceSchedule.objects.get(
        workspace_id=49
    )
    assert ws_schedule.enabled == True


@pytest.mark.django_db()
def test_async_update_workspace_name(mocker):
    mocker.patch(
        'apps.workspaces.tasks.get_fyle_admin',
        return_value={'data': {'org': {'name': 'Test Org'}}}
    )
    workspace = Workspace.objects.get(id=1)
    async_update_workspace_name(workspace, 'Bearer access_token')

    workspace = Workspace.objects.get(id=1)
    assert workspace.name == 'Test Org'


def test_async_create_admin_subcriptions(db, mocker):
    mocker.patch(
        'fyle.platform.apis.v1.admin.Subscriptions.post',
        return_value={}
    )
    async_create_admin_subcriptions(1)


@pytest.mark.django_db(databases=['default'])
def test_post_to_integration_settings(mocker):
    mocker.patch(
        'apps.fyle.helpers.post_request',
        return_value=''
    )

    no_exception = True
    post_to_integration_settings(1, True)

    # If exception is raised, this test will fail
    assert no_exception


@pytest.mark.django_db(databases=['default'])
def test_patch_integration_settings(mocker):
    """
    Test patch_integration_settings task
    """

    workspace_id = 1

    refresh_token = 'dummy_refresh_token'
    fyle_credential = FyleCredential.objects.get(workspace_id=workspace_id)
    fyle_credential.refresh_token = refresh_token
    fyle_credential.save()

    patch_request_mock = mocker.patch('apps.workspaces.tasks.patch_request')

    patch_integration_settings(workspace_id, errors=5)

    patch_request_mock.assert_not_called()

    workspace = Workspace.objects.get(id=workspace_id)
    workspace.onboarding_state = 'COMPLETE'
    workspace.save()

    patch_request_mock.reset_mock()
    patch_integration_settings(workspace_id, errors=5)
    
    patch_request_mock.assert_called_with(
        mocker.ANY,  # URL
        {
            'tpa_name': 'Fyle Netsuite Integration',
            'errors_count': 5
        },
        refresh_token
    )

    patch_request_mock.reset_mock()
    patch_integration_settings(workspace_id, is_token_expired=True)

    patch_request_mock.assert_called_with(
        mocker.ANY,  # URL
        {
            'tpa_name': 'Fyle Netsuite Integration',
            'is_token_expired': True
        },
        refresh_token
    )
    
    patch_request_mock.reset_mock()
    patch_integration_settings(workspace_id, errors=10, is_token_expired=False)

    patch_request_mock.assert_called_with(
        mocker.ANY,  # URL
        {
            'tpa_name': 'Fyle Netsuite Integration',
            'errors_count': 10,
            'is_token_expired': False
        },
        refresh_token
    )

    patch_request_mock.reset_mock()
    patch_request_mock.side_effect = Exception('Test exception')

    patch_integration_settings(workspace_id, errors=15)

    patch_request_mock.assert_called_once()

    patch_request_mock.reset_mock()
    patch_integration_settings(workspace_id, unmapped_card_count=10)

    patch_request_mock.assert_called_with(
        mocker.ANY,  # URL
        {
            'tpa_name': 'Fyle Netsuite Integration',
            'unmapped_card_count': 10
        },
        refresh_token
    )


@pytest.mark.django_db(databases=['default'])
def test_patch_integration_settings_for_unmapped_cards(mocker):
    """
    Test patch_integration_settings_for_unmapped_cards task
    """
    workspace_id = 1
    refresh_token = 'dummy_refresh_token'
    fyle_credential = FyleCredential.objects.get(workspace_id=workspace_id)
    fyle_credential.refresh_token = refresh_token
    fyle_credential.save()
    
    last_export_detail = LastExportDetail.objects.get(workspace_id=workspace_id)
    last_export_detail.unmapped_card_count = 10
    last_export_detail.save()

    patch_integration_settings_mock = mocker.patch('apps.workspaces.tasks.patch_integration_settings')
    patch_integration_settings_mock.return_value = True

    patch_integration_settings_for_unmapped_cards(workspace_id, unmapped_card_count=10)
    patch_integration_settings_mock.assert_called_once_with(
        workspace_id=workspace_id, 
        unmapped_card_count=10
    )
    last_export_detail.refresh_from_db()
    assert last_export_detail.unmapped_card_count == 10

    patch_integration_settings_mock.reset_mock()
    patch_integration_settings_for_unmapped_cards(workspace_id, unmapped_card_count=10)
    patch_integration_settings_mock.assert_not_called()

    patch_integration_settings_mock.return_value = False
    patch_integration_settings_mock.reset_mock()

    patch_integration_settings_for_unmapped_cards(workspace_id, unmapped_card_count=15)
    last_export_detail.refresh_from_db()
    assert last_export_detail.unmapped_card_count == 10

    patch_integration_settings_mock.return_value = True
    patch_integration_settings_mock.reset_mock()

    patch_integration_settings_for_unmapped_cards(workspace_id, unmapped_card_count=0)
    patch_integration_settings_mock.assert_called_once_with(
        workspace_id=workspace_id, 
        unmapped_card_count=0
    )

    last_export_detail.refresh_from_db()
    assert last_export_detail.unmapped_card_count == 0
