import logging
import json
import traceback

from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog, Error
from apps.workspaces.models import NetSuiteCredentials

from netsuitesdk.internal.exceptions import NetSuiteRequestError
from netsuitesdk import NetSuiteRateLimitError, NetSuiteLoginError
from fyle_netsuite_api.exceptions import BulkError

logger = logging.getLogger(__name__)
logger.level = logging.INFO

netsuite_error_message = 'NetSuite System Error'

def __handle_netsuite_connection_error(expense_group: ExpenseGroup, task_log: TaskLog) -> None:
    logger.info(
        'NetSuite Credentials not found for workspace_id %s / expense group %s',
        expense_group.id,
        expense_group.workspace_id
    )
    detail = {
        'expense_group_id': expense_group.id,
        'message': 'NetSuite Account not connected'
    }

    Error.objects.update_or_create(
        workspace_id=expense_group.workspace_id,
        expense_group=expense_group,
        defaults={
            'type': 'NETSUITE_ERROR',
            'error_title': netsuite_error_message,
            'error_detail': detail['message'],
            'is_resolved': False
        })

    task_log.status = 'FAILED'
    task_log.detail = detail

    task_log.save()


def __log_error(task_log: TaskLog) -> None:
    logger.exception('Something unexpected happened workspace_id: %s %s', task_log.workspace_id, task_log.detail)


def handle_netsuite_exceptions(payment=False):
    def decorator(func):
        def wrapper(*args):
            if payment:
                entity_object = args[0]
                workspace_id = args[1]
                object_type = args[2]
                task_log, _ = TaskLog.objects.update_or_create(
                                workspace_id=workspace_id,
                                task_id='PAYMENT_{}'.format(entity_object['unique_id']),
                                defaults={
                                    'status': 'IN_PROGRESS',
                                    'type': 'CREATING_VENDOR_PAYMENT'
                                }
                            )
            else:
                expense_group = args[0]
                task_log_id = args[1]
                task_log = TaskLog.objects.get(id=task_log_id)
            
            try:
                func(*args)
            
            except NetSuiteCredentials.DoesNotExist:
                if payment:
                    logger.info(
                        'NetSuite Credentials not found for workspace_id %s',
                        workspace_id
                    )
                    detail = {
                        'message': 'NetSuite Account not connected'
                    }
                    task_log.status = 'FAILED'
                    task_log.detail = detail

                    task_log.save()
                else:
                    __handle_netsuite_connection_error(expense_group, task_log)

            except (NetSuiteRequestError, NetSuiteLoginError) as exception:
                all_details = []
                logger.info({'error': exception})
                detail = json.dumps(exception.__dict__)
                detail = json.loads(detail)
                task_log.status = 'FAILED'

                all_details.append({
                    'value': netsuite_error_message,
                    'type': detail['code'],
                    'message': detail['message']
                })
                if not payment:
                    all_details[0]['expense_group_id'] = expense_group.id
                    Error.objects.update_or_create(
                    workspace_id=expense_group.workspace_id,
                    expense_group=expense_group,
                    defaults={
                        'type': 'NETSUITE_ERROR',
                        'error_title': netsuite_error_message,
                        'error_detail': detail['message'],
                        'is_resolved': False
                    }
                )
                task_log.detail = all_details

                task_log.save()

            except BulkError as exception:
                logger.info(exception.response)
                detail = exception.response
                task_log.status = 'FAILED'
                task_log.detail = detail

                task_log.save()

            except NetSuiteRateLimitError:
                if not payment:
                    Error.objects.update_or_create(
                    workspace_id=expense_group.workspace_id,
                    expense_group=expense_group,
                    defaults={
                        'type': 'NETSUITE_ERROR',
                        'error_title': netsuite_error_message,
                        'error_detail': f'Rate limit error, workspace_id - {expense_group.workspace_id}',
                        'is_resolved': False
                    }
                )
                logger.info('Rate limit error, workspace_id - %s', workspace_id if payment else expense_group.workspace_id)
                task_log.status = 'FAILED'
                task_log.detail = {
                    'error': 'Rate limit error'
                }

                task_log.save()

            except Exception:
                error = traceback.format_exc()
                task_log.detail = {
                    'error': error
                }
                task_log.status = 'FATAL'
                task_log.save()
                __log_error(task_log)

        return wrapper
    return decorator
