import pytest
from apps.tasks.models import TaskLog
from apps.users.models import User

@pytest.fixture
def create_task_logs(test_connection):
    TaskLog.objects.update_or_create(
        workspace_id=49,
        type='CREATING_EXPENSE_REPORT',
        defaults={
            'status': 'FAILED'
        }
    )

@pytest.fixture
def create_user():
    User.objects.create(
        user_id='usezCopk4qdF',
        email='owner@fyleforgotham.in',
        active=True,
        admin=True,
        staff=True
    )