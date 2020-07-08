import logging
from typing import List
import traceback
from datetime import datetime

from django.conf import settings
from django.db import transaction

from apps.workspaces.models import FyleCredential, Workspace
from apps.tasks.models import TaskLog

from .models import Expense, ExpenseGroup
from .utils import FyleConnector
from .serializers import ExpenseGroupSerializer

logger = logging.getLogger(__name__)


def schedule_expense_group_creation(workspace_id: int, user: str):
    """
    Schedule Expense group creation
    :param workspace_id: Workspace id
    :param user: User email
    :return: None
    """
    fyle_credentials = FyleCredential.objects.get(
        workspace_id=workspace_id)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token)
    fyle_sdk_connection = fyle_connector.connection

    jobs = fyle_sdk_connection.Jobs
    user_profile = fyle_sdk_connection.Employees.get_my_profile()['data']

    task_log = TaskLog.objects.create(
        workspace_id=workspace_id,
        type='FETCHING_EXPENSES',
        status='IN_PROGRESS'
    )

    created_job = jobs.trigger_now(
        callback_url='{0}{1}'.format(
            settings.API_URL,
            '/workspaces/{0}/fyle/expense_groups/'.format(workspace_id)
        ),
        callback_method='POST',
        object_id=task_log.id,
        payload={
            'task_log_id': task_log.id
        },
        job_description='Fetch expenses: Workspace id - {0}, user - {1}'.format(
            workspace_id, user
        ),
        org_user_id=user_profile['id']
    )
    task_log.task_id = created_job['id']
    task_log.save()


def create_expense_groups(workspace_id: int, state: List[str], export_non_reimbursable: bool, task_log: TaskLog):
    """
    Create expense groups
    :param task_log: Task log object
    :param workspace_id: workspace id
    :param state: expense state
    :param export_non_reimbursable: true / false
    :return: task log
    """

    async_create_expense_groups(workspace_id, state, export_non_reimbursable, task_log)

    task_log.detail = {
        'message': 'Creating expense groups'
    }
    task_log.save(update_fields=['task_id', 'detail'])

    return task_log


def async_create_expense_groups(workspace_id: int, state: List[str], export_non_reimbursable: bool, task_log: TaskLog):
    try:
        with transaction.atomic():

            workspace = Workspace.objects.get(pk=workspace_id)

            last_synced_at = workspace.last_synced_at

            updated_at = []

            if last_synced_at:
                updated_at.append('gte:{0}'.format(datetime.strftime(last_synced_at, '%Y-%m-%dT%H:%M:%S.000Z')))

            workspace.last_synced_at = datetime.now()
            workspace.save()

            fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)

            fyle_connector = FyleConnector(fyle_credentials.refresh_token)

            expenses = fyle_connector.get_expenses(
                state=state, export_non_reimbursable=export_non_reimbursable, updated_at=updated_at
            )

            expense_objects = Expense.create_expense_objects(expenses)

            expense_group_objects = ExpenseGroup.create_expense_groups_by_report_id(
                expense_objects, workspace_id
            )

            task_log.detail = ExpenseGroupSerializer(expense_group_objects, many=True).data

            task_log.status = 'COMPLETE'

            task_log.save(update_fields=['detail', 'status'])

    except FyleCredential.DoesNotExist:
        logger.exception('Fyle credentials not found %s', workspace_id)
        task_log.detail = {
            'message': 'Fyle credentials do not exist in workspace'
        }
        task_log.status = 'FAILED'
        task_log.save(update_fields=['detail', 'status'])

    except Exception:
        error = traceback.format_exc()
        task_log.detail = {
            'error': error
        }
        task_log.status = 'FATAL'
        task_log.save(update_fields=['detail', 'status'])
        logger.exception('Something unexpected happened workspace_id: %s\n%s', task_log.workspace_id, error)
