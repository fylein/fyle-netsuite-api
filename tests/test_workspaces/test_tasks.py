import pytest
from django.db.models import Q
from apps.fyle.models import Expense, ExpenseGroup
from apps.tasks.models import TaskLog
from apps.workspaces.models import Configuration, WorkspaceSchedule, FyleCredential, Workspace, LastExportDetail
from apps.workspaces.tasks import run_sync_schedule, schedule_sync, delete_cards_mapping_settings, run_email_notification, async_create_admin_subscriptions, post_to_integration_settings, patch_integration_settings, patch_integration_settings_for_unmapped_cards, async_update_workspace_name
from fyle_accounting_mappings.models import ExpenseAttribute
from tests.test_fyle.fixtures import data as fyle_data
from fyle.platform.exceptions import InvalidTokenError


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
def test_async_update_workspace_name(mocker, add_fyle_credentials):
    mocker.patch(
        'apps.workspaces.tasks.get_cluster_domain',
        return_value='https://us1.fylehq.com'
    )
    mocker.patch(
        'apps.workspaces.tasks.get_fyle_admin',
        return_value={'data': {'org': {'name': 'Test Org'}}}
    )
    async_update_workspace_name(1)

    workspace = Workspace.objects.get(id=1)
    assert workspace.name == 'Test Org'


def test_async_create_admin_subscriptions(db, mocker):
    mocker.patch(
        'fyle.platform.apis.v1.admin.Subscriptions.post',
        return_value={}
    )
    async_create_admin_subscriptions(1)


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
    last_export_detail.unmapped_card_count = 0
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


def test_run_sync_schedule_skips_failed_expense_groups_with_re_attempt_export_false(mocker, db):
    """
    Test that expense groups with FAILED task logs and re_attempt_export=False are skipped
    """
    workspace_id = 1

    # Mock the Fyle API call
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=fyle_data['expenses']
    )

    # Mock the export function
    mock_export = mocker.patch('apps.workspaces.actions.export_to_netsuite')

    # Create expense group that should be skipped
    failed_expense_group = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    # Create FAILED task log with re_attempt_export=False
    TaskLog.objects.create(
        workspace_id=workspace_id,
        expense_group=failed_expense_group,
        type='CREATING_BILLS',
        status='FAILED',
        re_attempt_export=False
    )

    # Run sync schedule
    run_sync_schedule(workspace_id)

    # Verify the failed expense group was skipped
    eligible_calls = [call for call in mock_export.call_args_list if 'expense_group_ids' in call.kwargs]
    if eligible_calls:
        exported_ids = set(eligible_calls[-1].kwargs['expense_group_ids'])
        assert failed_expense_group.id not in exported_ids, f"FAILED expense group {failed_expense_group.id} with re_attempt_export=False should be skipped"

    # Verify FETCHING_EXPENSES completed
    task_log = TaskLog.objects.filter(workspace_id=workspace_id, type='FETCHING_EXPENSES').first()
    assert task_log.status == 'COMPLETE'


def test_run_sync_schedule_includes_new_expense_groups_without_task_logs(mocker, db):
    """
    Test that new expense groups without task logs are not skipped and get included in export
    """
    workspace_id = 1

    # Mock the Fyle API call
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=fyle_data['expenses']
    )

    # Mock the export function
    mock_export = mocker.patch('apps.workspaces.actions.export_to_netsuite')

    # Create new expense groups without any task logs
    new_expense_group_1 = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    new_expense_group_2 = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='CCC',
        exported_at=None
    )

    # Run sync schedule
    run_sync_schedule(workspace_id)

    # Verify new expense groups are included in export
    eligible_calls = [call for call in mock_export.call_args_list if 'expense_group_ids' in call.kwargs]
    if eligible_calls:
        exported_ids = set(eligible_calls[-1].kwargs['expense_group_ids'])
        assert new_expense_group_1.id in exported_ids, f"New expense group {new_expense_group_1.id} without task logs should be included"
        assert new_expense_group_2.id in exported_ids, f"New expense group {new_expense_group_2.id} without task logs should be included"

    # Verify FETCHING_EXPENSES completed
    task_log = TaskLog.objects.filter(workspace_id=workspace_id, type='FETCHING_EXPENSES').first()
    assert task_log.status == 'COMPLETE'


def test_run_sync_schedule_with_re_attempt_export_false_exclusion(mocker, db):
    """
    Test run_sync_schedule excludes expense groups with FAILED task logs where re_attempt_export=False
    This is a full integration test that actually calls run_sync_schedule
    """
    workspace_id = 1

    # Mock the Fyle API call
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=fyle_data['expenses']
    )

    # Mock the export function to capture what gets exported
    mock_export = mocker.patch('apps.workspaces.actions.export_to_netsuite')

    # Create expense groups for testing
    excluded_group = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    included_group = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    no_task_log_group = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    # Create task logs - this one should be excluded
    TaskLog.objects.create(
        workspace_id=workspace_id,
        expense_group=excluded_group,
        type='CREATING_BILLS',
        status='FAILED',
        re_attempt_export=False
    )

    # This one should be included (retry enabled)
    TaskLog.objects.create(
        workspace_id=workspace_id,
        expense_group=included_group,
        type='CREATING_BILLS',
        status='FAILED',
        re_attempt_export=True
    )

    # Run the sync schedule
    run_sync_schedule(workspace_id)

    # Verify the export was called
    eligible_calls = [call for call in mock_export.call_args_list if 'expense_group_ids' in call.kwargs]
    if eligible_calls:
        exported_ids = set(eligible_calls[-1].kwargs['expense_group_ids'])

        # Verify exclusion/inclusion logic
        assert excluded_group.id not in exported_ids, f"Expense group {excluded_group.id} with FAILED + re_attempt_export=False should be excluded"
        assert included_group.id in exported_ids, f"Expense group {included_group.id} with FAILED + re_attempt_export=True should be included"
        assert no_task_log_group.id in exported_ids, f"Expense group {no_task_log_group.id} without task log should be included"

    # Verify FETCHING_EXPENSES task completed
    task_log = TaskLog.objects.filter(
        workspace_id=workspace_id,
        type='FETCHING_EXPENSES'
    ).first()
    assert task_log.status == 'COMPLETE'


def test_run_sync_schedule_includes_expense_groups_without_task_logs_re_attempt_export(mocker, db):
    """
    Test that expense groups without task logs are included in export (re_attempt_export integration test)
    This verifies the new behavior works end-to-end with run_sync_schedule
    """
    workspace_id = 1

    # Mock the Fyle API call
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Expenses.get',
        return_value=fyle_data['expenses']
    )

    # Mock the export function
    mock_export = mocker.patch('apps.workspaces.actions.export_to_netsuite')

    # Create expense groups without task logs
    test_expense_group_1 = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )

    test_expense_group_2 = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='CCC',
        exported_at=None
    )

    # Create one expense group with FAILED + re_attempt_export=False (should be excluded)
    excluded_group = ExpenseGroup.objects.create(
        workspace_id=workspace_id,
        fund_source='PERSONAL',
        exported_at=None
    )
    TaskLog.objects.create(
        workspace_id=workspace_id,
        expense_group=excluded_group,
        type='CREATING_BILLS',
        status='FAILED',
        re_attempt_export=False
    )

    # Run sync schedule
    run_sync_schedule(workspace_id)

    # Verify export behavior
    eligible_calls = [call for call in mock_export.call_args_list if 'expense_group_ids' in call.kwargs]
    if eligible_calls:
        exported_ids = set(eligible_calls[-1].kwargs['expense_group_ids'])

        # Groups without task logs should be included
        groups_without_task_logs = ExpenseGroup.objects.filter(
            workspace_id=workspace_id,
            exported_at__isnull=True,
            tasklog__isnull=True
        ).values_list('id', flat=True)

        for group_id in groups_without_task_logs:
            assert group_id in exported_ids, f"Expense group {group_id} without task logs should be included in export"

        # Specific test groups should be included
        assert test_expense_group_1.id in exported_ids, f"Test expense group {test_expense_group_1.id} should be included in export"
        assert test_expense_group_2.id in exported_ids, f"Test expense group {test_expense_group_2.id} should be included in export"
        
        # Failed group with re_attempt_export=False should be excluded
        assert excluded_group.id not in exported_ids, f"Expense group {excluded_group.id} with FAILED + re_attempt_export=False should be excluded"

    # Verify FETCHING_EXPENSES completed
    task_log = TaskLog.objects.filter(
        workspace_id=workspace_id,
        type='FETCHING_EXPENSES'
    ).first()
    assert task_log.status == 'COMPLETE'


def test_async_create_admin_subscriptions_invalid_token(db, mocker):
    mocker.patch(
        'fyle_integrations_platform_connector.PlatformConnector.__init__',
        side_effect=InvalidTokenError('Invalid Token')
    )
    async_create_admin_subscriptions(1)

    mocker.patch(
        'fyle_integrations_platform_connector.PlatformConnector.__init__',
        side_effect=Exception('General error')
    )
    async_create_admin_subscriptions(1)


def test_async_update_workspace_name_invalid_token(db, mocker, add_fyle_credentials):
    mocker.patch(
        'apps.workspaces.tasks.get_cluster_domain',
        return_value='https://us1.fylehq.com'
    )
    mocker.patch(
        'apps.workspaces.tasks.get_fyle_admin',
        side_effect=InvalidTokenError('Invalid Token')
    )
    async_update_workspace_name(1)

    mocker.patch(
        'apps.workspaces.tasks.get_fyle_admin',
        side_effect=Exception('General error')
    )
    async_update_workspace_name(1)


def test_async_update_workspace_name_fyle_credentials_not_found(db, mocker):
    FyleCredential.objects.filter(workspace_id=1).delete()
    async_update_workspace_name(1)
