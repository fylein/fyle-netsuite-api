import logging
import json
import traceback
import zeep.exceptions as zeep_exceptions

from django.db.models import Q, F

from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog, Error
from apps.workspaces.models import Configuration, LastExportDetail, NetSuiteCredentials

from netsuitesdk.internal.exceptions import NetSuiteRequestError
from netsuitesdk import NetSuiteRateLimitError, NetSuiteLoginError
from fyle_netsuite_api.exceptions import BulkError
from fyle_netsuite_api.utils import invalidate_netsuite_credentials

from .actions import update_last_export_details
from apps.fyle.actions import update_failed_expenses, post_accounting_export_summary

from .errors import error_matcher, get_entity_values, replace_destination_id_with_values

logger = logging.getLogger(__name__)
logger.level = logging.INFO

netsuite_error_message = 'NetSuite System Error'

def __handle_netsuite_connection_error(expense_group: ExpenseGroup, task_log: TaskLog, workspace_id: int) -> None:

    if expense_group:
        logger.info(
            'NetSuite Credentials not found for workspace_id %s / expense group %s',
            expense_group.id,
            expense_group.workspace_id
        )
    else:
        logger.info(
            'NetSuite Credentials not found for workspace_id %s',
            workspace_id
        )
    detail = {
        'message': 'NetSuite Account not connected'
    }

    if expense_group:
        error, created = Error.objects.update_or_create(
            workspace_id=expense_group.workspace_id,
            expense_group=expense_group,
            defaults={
                'type': 'NETSUITE_ERROR',
                'error_title': netsuite_error_message,
                'error_detail': detail['message'],
                'is_resolved': False
            })

        error.increase_repetition_count_by_one(created)

    task_log.status = 'FAILED'
    task_log.re_attempt_export = False
    task_log.detail = detail

    task_log.save()


def __log_error(task_log: TaskLog) -> None:
    logger.exception('Something unexpected happened workspace_id: %s %s', task_log.workspace_id, task_log.detail)


def parse_error(message, workspace_id, expense_group):

    export_types = {
        'EXPENSE REPORT' : 'expense_report',
        'JOURNAL ENTRY': 'journal_entry',
        'BILL': 'bills',
        'CREDIT CARD CHARGE': 'credit_card_charge'
    }
    
    fund_source = expense_group.fund_source
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    if fund_source == 'PERSONAL':
        configuration_export_type = Configuration.objects.get(workspace_id=workspace_id).reimbursable_expenses_object
    else:
        configuration_export_type = Configuration.objects.get(workspace_id=workspace_id).corporate_credit_card_expenses_object
    
    if configuration_export_type not in export_types.keys():
        return []

    export_type = export_types[configuration_export_type]

    error_dict, article_link = error_matcher(message, export_type, configuration)
    entities = get_entity_values(error_dict, workspace_id, configuration)
    message = replace_destination_id_with_values(message, entities)
    return message, article_link

def handle_netsuite_exceptions(payment=False):
    def decorator(func):
        def wrapper(*args):
            if payment:
                entity_object = args[0]
                workspace_id = args[1]
                object_type = args[2]
                expense_group = None
                task_log, _ = TaskLog.objects.update_or_create(
                workspace_id=workspace_id,
                task_id='PAYMENT_{}'.format(entity_object['unique_id']),
                defaults={
                    'status': 'IN_PROGRESS',
                    'type': 'CREATING_VENDOR_PAYMENT'
                    }
                )
            else:
                task_log_id = args[1]
                task_log = TaskLog.objects.get(id=task_log_id)
                expense_group_id = args[0]
                expense_group = ExpenseGroup.objects.get(id=expense_group_id, workspace_id=task_log.workspace_id)
                workspace_id=expense_group.workspace_id
                last_export = args[2]
            
            try:
                func(*args)
            
            except NetSuiteCredentials.DoesNotExist:
                    __handle_netsuite_connection_error(expense_group, task_log, workspace_id)

            except (NetSuiteRequestError, NetSuiteLoginError) as exception:
                all_details = []
                is_parsed = False
                logger.info({'error': exception})
                detail = json.dumps(exception.__dict__)
                detail = json.loads(detail)

                if isinstance(exception, NetSuiteLoginError):
                    invalidate_netsuite_credentials(workspace_id if payment else expense_group.workspace_id)

                task_log.status = 'FAILED'
                task_log.re_attempt_export = False

                all_details.append({
                    'value': netsuite_error_message,
                    'type': detail['code'],
                    'message': detail['message']
                })
                if not payment:
                    parsed_message, article_link = parse_error(detail['message'], expense_group.workspace_id, expense_group)
                    if parsed_message:
                        is_parsed = True
                        all_details[-1]['message'] = parsed_message
                    error, created = Error.objects.update_or_create(
                        workspace_id=expense_group.workspace_id,
                        expense_group=expense_group,
                        defaults={
                                'type': 'NETSUITE_ERROR',
                                'error_title': netsuite_error_message,
                                'error_detail': parsed_message if is_parsed else detail['message'],
                                'is_resolved': False,
                                'is_parsed': is_parsed,
                                'article_link': article_link
                            }
                        )

                    error.increase_repetition_count_by_one(created)

                task_log.detail = all_details

                task_log.save()
                if not payment:
                    update_failed_expenses(expense_group.expenses.all(), False)


            except BulkError as exception:
                logger.info(exception.response)
                detail = exception.response
                task_log.status = 'FAILED'
                task_log.re_attempt_export = False
                task_log.detail = detail

                task_log.save()
                if not payment:
                    update_failed_expenses(expense_group.expenses.all(), True)

            except NetSuiteRateLimitError:
                if not payment:
                    error, created = Error.objects.update_or_create(
                        workspace_id=expense_group.workspace_id,
                        expense_group=expense_group,
                        defaults={
                            'type': 'NETSUITE_ERROR',
                            'error_title': netsuite_error_message,
                            'error_detail': f'Rate limit error, workspace_id - {expense_group.workspace_id}',
                            'is_resolved': False
                        }
                    )
                    error.increase_repetition_count_by_one(created)

                logger.info('Rate limit error, workspace_id - %s', workspace_id if payment else expense_group.workspace_id)
                task_log.status = 'FAILED'
                task_log.re_attempt_export = False
                task_log.detail = {
                    'error': 'Rate limit error'
                }

                task_log.save()
                if not payment:
                    update_failed_expenses(expense_group.expenses.all(), False)

            except zeep_exceptions.Fault as exception:
                task_log.status = 'FAILED'
                task_log.re_attempt_export = False
                detail = 'Zeep Fault error'
                logger.info(f'Error while exporting: {exception.__dict__}')
                try:
                    detail = "{0} {1}".format(exception.message, exception.code)
                    logger.info(f'Error while exporting: {detail}')
                except Exception:
                    logger.info(f'Error while exporting: {detail}')

                task_log.detail = detail
                task_log.save()

                error, created = Error.objects.update_or_create(
                    workspace_id=workspace_id,
                    expense_group=expense_group,
                    defaults={
                        'type': 'NETSUITE_ERROR',
                        'error_title': 'Something unexpected has happened during export',
                        'error_detail': f'{detail}, workspace_id - {workspace_id}',
                        'is_resolved': False
                    }
                )
                error.increase_repetition_count_by_one(created)

            except Exception:
                error = traceback.format_exc()
                task_log.detail = {
                    'error': error
                }
                task_log.status = 'FATAL'
                task_log.save()
                if not payment:
                    update_failed_expenses(expense_group.expenses.all(), False)
                __log_error(task_log)
            
            if not payment:
                post_accounting_export_summary(workspace_id=expense_group.workspace_id, expense_ids=[expense.id for expense in expense_group.expenses.all()], fund_source=expense_group.fund_source, is_failed=True)
            
            if not payment and last_export is True:
                update_last_export_details(expense_group.workspace_id)

        return wrapper
    return decorator
