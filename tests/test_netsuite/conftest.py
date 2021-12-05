import pytest

from apps.tasks.models import TaskLog

@pytest.fixture
def create_task_logs(db):
    TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

    TaskLog.objects.update_or_create(
        workspace_id=2,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

    TaskLog.objects.update_or_create(
        workspace_id=49,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'READY'
        }
    )

