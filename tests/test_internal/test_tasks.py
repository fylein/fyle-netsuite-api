from datetime import datetime, timedelta, timezone
from unittest import mock

from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog
from apps.internal.tasks import re_export_stuck_exports


def test_no_stuck_exports(db, mocker):
    mock_export = mocker.patch('apps.internal.tasks.export_to_netsuite')
    mock_update_failed = mocker.patch('apps.internal.tasks.update_failed_expenses')
    mock_post_summary = mocker.patch('apps.internal.tasks.post_accounting_export_summary')
    
    re_export_stuck_exports()
    
    mock_export.assert_not_called()
    mock_update_failed.assert_not_called()
    mock_post_summary.assert_not_called()


def test_stuck_export_found_and_reexported(
    db, mocker, create_workspace_for_stuck_export, create_expense_group_with_expenses
):
    workspace = create_workspace_for_stuck_export
    expense_group = create_expense_group_with_expenses
    
    stuck_time = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
    task_log = TaskLog.objects.create(
        workspace_id=workspace.id,
        expense_group_id=expense_group.id,
        type='CREATING_BILL',
        status='ENQUEUED',
        stuck_export_re_attempt_count=0
    )
    TaskLog.objects.filter(id=task_log.id).update(updated_at=stuck_time)
    
    mock_export = mocker.patch('apps.internal.tasks.export_to_netsuite')
    mock_update_failed = mocker.patch('apps.internal.tasks.update_failed_expenses')
    mock_post_summary = mocker.patch('apps.internal.tasks.post_accounting_export_summary')
    mocker.patch('apps.internal.tasks.OrmQ.objects.all', return_value=[])
    mocker.patch('apps.internal.tasks.Schedule.objects.filter', return_value=mock.Mock(filter=mock.Mock(return_value=mock.Mock(first=mock.Mock(return_value=None)))))
    
    re_export_stuck_exports()
    
    task_log.refresh_from_db()
    assert task_log.status == 'FAILED'
    assert task_log.re_attempt_export == True
    assert task_log.stuck_export_re_attempt_count == 1
    
    mock_update_failed.assert_called_once()
    mock_post_summary.assert_called_once()
    mock_export.assert_called_once()


def test_max_attempts_limit_excludes_task(
    db, mocker, create_workspace_for_stuck_export, create_expense_group_with_expenses
):
    workspace = create_workspace_for_stuck_export
    expense_group = create_expense_group_with_expenses
    
    stuck_time = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
    task_log = TaskLog.objects.create(
        workspace_id=workspace.id,
        expense_group_id=expense_group.id,
        type='CREATING_BILL',
        status='ENQUEUED',
        stuck_export_re_attempt_count=2
    )
    TaskLog.objects.filter(id=task_log.id).update(updated_at=stuck_time)
    
    mock_export = mocker.patch('apps.internal.tasks.export_to_netsuite')
    mock_update_failed = mocker.patch('apps.internal.tasks.update_failed_expenses')
    mock_post_summary = mocker.patch('apps.internal.tasks.post_accounting_export_summary')
    
    re_export_stuck_exports()
    
    mock_export.assert_not_called()
    mock_update_failed.assert_not_called()
    mock_post_summary.assert_not_called()
    
    task_log.refresh_from_db()
    assert task_log.status == 'ENQUEUED'
    assert task_log.stuck_export_re_attempt_count == 2


def test_test_workspace_excluded(db, mocker, create_test_workspace):
    workspace = create_test_workspace
    
    expense_group = ExpenseGroup.objects.create(
        workspace_id=workspace.id,
        fund_source='PERSONAL',
        exported_at=None,
    )
    
    stuck_time = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
    task_log = TaskLog.objects.create(
        workspace_id=workspace.id,
        expense_group_id=expense_group.id,
        type='CREATING_BILL',
        status='ENQUEUED',
        stuck_export_re_attempt_count=0
    )
    TaskLog.objects.filter(id=task_log.id).update(updated_at=stuck_time)
    
    mock_export = mocker.patch('apps.internal.tasks.export_to_netsuite')
    mock_update_failed = mocker.patch('apps.internal.tasks.update_failed_expenses')
    
    re_export_stuck_exports()
    
    mock_export.assert_not_called()
    mock_update_failed.assert_not_called()
    
    task_log.refresh_from_db()
    assert task_log.status == 'ENQUEUED'


def test_in_progress_status_also_considered_stuck(
    db, mocker, create_workspace_for_stuck_export, create_expense_group_with_expenses
):
    workspace = create_workspace_for_stuck_export
    expense_group = create_expense_group_with_expenses
    
    stuck_time = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
    task_log = TaskLog.objects.create(
        workspace_id=workspace.id,
        expense_group_id=expense_group.id,
        type='CREATING_BILL',
        status='IN_PROGRESS',
        stuck_export_re_attempt_count=0
    )
    TaskLog.objects.filter(id=task_log.id).update(updated_at=stuck_time)
    
    mocker.patch('apps.internal.tasks.export_to_netsuite')
    mocker.patch('apps.internal.tasks.update_failed_expenses')
    mocker.patch('apps.internal.tasks.post_accounting_export_summary')
    mocker.patch('apps.internal.tasks.OrmQ.objects.all', return_value=[])
    mocker.patch('apps.internal.tasks.Schedule.objects.filter', return_value=mock.Mock(filter=mock.Mock(return_value=mock.Mock(first=mock.Mock(return_value=None)))))

    re_export_stuck_exports()

    task_log.refresh_from_db()
    assert task_log.status == 'FAILED'
    assert task_log.stuck_export_re_attempt_count == 1


def test_task_updated_recently_not_considered_stuck(
    db, mocker, create_workspace_for_stuck_export, create_expense_group_with_expenses
):
    workspace = create_workspace_for_stuck_export
    expense_group = create_expense_group_with_expenses
    
    recent_time = datetime.now(tz=timezone.utc) - timedelta(minutes=30)
    task_log = TaskLog.objects.create(
        workspace_id=workspace.id,
        expense_group_id=expense_group.id,
        type='CREATING_BILL',
        status='ENQUEUED',
        stuck_export_re_attempt_count=0
    )
    TaskLog.objects.filter(id=task_log.id).update(updated_at=recent_time)
    
    mock_export = mocker.patch('apps.internal.tasks.export_to_netsuite')
    
    re_export_stuck_exports()
    
    mock_export.assert_not_called()
    
    task_log.refresh_from_db()
    assert task_log.status == 'ENQUEUED'


def test_task_older_than_7_days_not_considered(
    db, mocker, create_workspace_for_stuck_export, create_expense_group_with_expenses
):
    workspace = create_workspace_for_stuck_export
    expense_group = create_expense_group_with_expenses
    
    old_time = datetime.now(tz=timezone.utc) - timedelta(days=10)
    task_log = TaskLog.objects.create(
        workspace_id=workspace.id,
        expense_group_id=expense_group.id,
        type='CREATING_BILL',
        status='ENQUEUED',
        stuck_export_re_attempt_count=0
    )
    TaskLog.objects.filter(id=task_log.id).update(updated_at=old_time)
    
    mock_export = mocker.patch('apps.internal.tasks.export_to_netsuite')
    
    re_export_stuck_exports()
    
    mock_export.assert_not_called()
    
    task_log.refresh_from_db()
    assert task_log.status == 'ENQUEUED'


def test_attempt_count_increments_on_each_retry(
    db, mocker, create_workspace_for_stuck_export, create_expense_group_with_expenses
):
    workspace = create_workspace_for_stuck_export
    expense_group = create_expense_group_with_expenses
    
    stuck_time = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
    task_log = TaskLog.objects.create(
        workspace_id=workspace.id,
        expense_group_id=expense_group.id,
        type='CREATING_BILL',
        status='ENQUEUED',
        stuck_export_re_attempt_count=1
    )
    TaskLog.objects.filter(id=task_log.id).update(updated_at=stuck_time)
    
    mocker.patch('apps.internal.tasks.export_to_netsuite')
    mocker.patch('apps.internal.tasks.update_failed_expenses')
    mocker.patch('apps.internal.tasks.post_accounting_export_summary')
    mocker.patch('apps.internal.tasks.OrmQ.objects.all', return_value=[])
    mocker.patch('apps.internal.tasks.Schedule.objects.filter', return_value=mock.Mock(filter=mock.Mock(return_value=mock.Mock(first=mock.Mock(return_value=None)))))
    
    re_export_stuck_exports()
    
    task_log.refresh_from_db()
    assert task_log.stuck_export_re_attempt_count == 2
