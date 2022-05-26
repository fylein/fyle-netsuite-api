import pytest
from apps.tasks.models import TaskLog
from apps.users.models import User

@pytest.fixture
def create_task_logs(access_token):
    TaskLog.objects.update_or_create(
        workspace_id=49,
        type='CREATING_EXPENSE_REPORT',
        defaults={
            'status': 'FAILED'
        }
    )
