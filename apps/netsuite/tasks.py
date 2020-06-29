import logging
import traceback
from typing import List

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from fyle_accounting_mappings.models import Mapping

from fyle_netsuite_api.exceptions import BulkError

from apps.fyle.utils import FyleConnector
from apps.fyle.models import ExpenseGroup
from apps.mappings.models import GeneralMapping, SubsidiaryMapping
from apps.tasks.models import TaskLog
from apps.workspaces.models import NetSuiteCredentials, FyleCredential

from .models import Bill, BillLineitem
from .utils import NetSuiteConnector

logger = logging.getLogger(__name__)


def create_bill(expense_group, task_log):
    try:
        with transaction.atomic():
            __validate_expense_group(expense_group)

            bill_object = Bill.create_bill(expense_group)

            bill_lineitems_objects = BillLineitem.create_bill_lineitems(expense_group)

            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)

            netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)

            created_bill = netsuite_connection.post_bill(bill_object, bill_lineitems_objects)

            task_log.detail = created_bill
            task_log.bill = bill_object
            task_log.status = 'COMPLETE'

            task_log.save(update_fields=['detail', 'bill', 'status'])

    except NetSuiteCredentials.DoesNotExist:
        logger.exception(
            'NetSuite Credentials not found for workspace_id %s / expense group %s',
            expense_group.id,
            expense_group.workspace_id
        )
        detail = {
            'expense_group_id': expense_group.id,
            'message': 'NetSuite Account not connected'
        }
        task_log.status = 'FAILED'
        task_log.detail = detail

        task_log.save(update_fields=['detail', 'status'])

    except BulkError as exception:
        logger.error(exception.response)
        detail = exception.response
        task_log.status = 'FAILED'
        task_log.detail = detail

        task_log.save(update_fields=['detail', 'status'])

    except Exception:
        error = traceback.format_exc()
        task_log.detail = {
            'error': error
        }
        task_log.status = 'FATAL'
        task_log.save(update_fields=['detail', 'status'])
        logger.exception('Something unexpected happened workspace_id: %s\n%s', task_log.workspace_id, error)


def __validate_expense_group(expense_group: ExpenseGroup):
    bulk_errors = []
    row = 0

    try:
        GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
    except GeneralMapping.DoesNotExist:
        bulk_errors.append({
            'row': None,
            'expense_group_id': expense_group.id,
            'value': 'general mappings',
            'type': 'General Mappings',
            'message': 'General mappings not found'
        })

    try:
        SubsidiaryMapping.objects.get(workspace_id=expense_group.workspace_id)
    except SubsidiaryMapping.DoesNotExist:
        bulk_errors.append({
            'row': None,
            'expense_group_id': expense_group.id,
            'value': 'subsidiary mappings',
            'type': 'Subsidiary Mappings',
            'message': 'Subsidiary mapping not found'
        })

    try:
        Mapping.objects.get(
            Q(destination_type='VENDOR') | Q(destination_type='EMPLOYEE'),
            source_type='EMPLOYEE',
            source__value=expense_group.description.get('employee_email'),
            workspace_id=expense_group.workspace_id
        )
    except Mapping.DoesNotExist:
        bulk_errors.append({
            'row': None,
            'expense_group_id': expense_group.id,
            'value': expense_group.description.get('employee_email'),
            'type': 'Employee Mapping',
            'message': 'Employee mapping not found'
        })

    expenses = expense_group.expenses.all()

    for lineitem in expenses:
        category = lineitem.category if lineitem.category == lineitem.sub_category else '{0} / {1}'.format(
            lineitem.category, lineitem.sub_category)

        account = Mapping.objects.filter(
            source_type='CATEGORY',
            source__value=category,
            workspace_id=expense_group.workspace_id
        ).first()
        if not account:
            bulk_errors.append({
                'row': row,
                'expense_group_id': expense_group.id,
                'value': category,
                'type': 'Category Mapping',
                'message': 'Category Mapping not found'
            })

        row = row + 1

    if bulk_errors:
        raise BulkError('Mappings are missing', bulk_errors)


def schedule_bills_creation(workspace_id: int, expense_group_ids: List[str], user):
    """
    Schedule bills creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :param user: user email
    :return: None
    """
    if expense_group_ids:
        expense_groups = ExpenseGroup.objects.filter(
            workspace_id=workspace_id, id__in=expense_group_ids, bill__id__isnull=True
        ).all()
    else:
        expense_groups = ExpenseGroup.objects.filter(
            workspace_id=workspace_id, bill__id__isnull=True
        ).all()

    fyle_credentials = FyleCredential.objects.get(
        workspace_id=workspace_id)
    fyle_connector = FyleConnector(fyle_credentials.refresh_token, workspace_id)
    fyle_sdk_connection = fyle_connector.connection
    jobs = fyle_sdk_connection.Jobs
    user_profile = fyle_sdk_connection.Employees.get_my_profile()['data']

    for expense_group in expense_groups:
        task_log, _ = TaskLog.objects.update_or_create(
            workspace_id=expense_group.workspace_id,
            expense_group=expense_group,
            defaults={
                'status': 'IN_PROGRESS',
                'type': 'CREATING_BILL'
            }
        )
        created_job = jobs.trigger_now(
            callback_url='{0}{1}'.format(settings.API_URL, '/workspaces/{0}/netsuite/bills/'.format(workspace_id)),
            callback_method='POST', object_id=task_log.id, payload={
                'expense_group_id': expense_group.id,
                'task_log_id': task_log.id
            }, job_description='Create Bill: Workspace id - {0}, user - {1}, expense group id - {2}'.format(
                workspace_id, user, expense_group.id
            ),
            org_user_id=user_profile['id']
        )
        task_log.task_id = created_job['id']
        task_log.save()
