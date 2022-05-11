import pytest
from apps.tasks.models import TaskLog

@pytest.fixture
def create_task_logs(test_connection):
    TaskLog.objects.update_or_create(
        workspace_id=49,
        type='CREATING_EXPENSE_REPORT',
        defaults={
            'status': 'FAILED'
        }
    )