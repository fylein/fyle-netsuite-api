
import pytest
from apps.tasks.models import TaskLog

@pytest.fixture
def create_task_logs(django_db_setup, test_connection):
    TaskLog.objects.update_or_create(
        workspace_id=1,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'IN_PROGRESS'
        }
    )
