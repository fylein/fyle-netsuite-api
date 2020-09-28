import json
import logging
import traceback
from typing import List
import base64

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from fylesdk import FyleSDKError

from netsuitesdk.internal.exceptions import NetSuiteRequestError

from fyle_accounting_mappings.models import Mapping

from fyle_netsuite_api.exceptions import BulkError

from apps.fyle.utils import FyleConnector
from apps.fyle.models import ExpenseGroup
from apps.mappings.models import GeneralMapping, SubsidiaryMapping
from apps.tasks.models import TaskLog
from apps.workspaces.models import NetSuiteCredentials, FyleCredential, WorkspaceGeneralSettings

from .models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem, JournalEntry, JournalEntryLineItem
from .utils import NetSuiteConnector

logger = logging.getLogger(__name__)


def load_attachments(netsuite_connection: NetSuiteConnector, expense_id: str, expense_group: ExpenseGroup):
    """
    Get attachments from Fyle
    :param netsuite_connection: NetSuite Connection
    :param expense_id: Fyle expense id
    :param expense_group: Integration Expense group
    """
    workspace_id = expense_group.workspace_id
    try:
        fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
        fyle_connector = FyleConnector(fyle_credentials.refresh_token, workspace_id)
        attachment = fyle_connector.get_attachment(expense_id)

        folder = netsuite_connection.connection.folders.post({
            "externalId": '{}-{}-{}'.format(workspace_id, expense_group.id, expense_group.description['claim_number']),
            "name": '{}-{}-{}'.format(workspace_id, expense_group.id, expense_group.description['claim_number'])
        })
        if attachment:
            netsuite_connection.connection.files.post({
                "externalId": expense_id,
                "name": attachment['filename'],
                'content': base64.b64decode(attachment['content']),
                "folder": {
                            "name": None,
                            "internalId": folder['internalId'],
                            "externalId": folder['externalId'],
                            "type": "folder"
                        }
                }
            )

            file = netsuite_connection.connection.files.get(externalId=expense_id)
            return file['url']
    except Exception:
        error = traceback.format_exc()
        logger.error(
            'Attachment failed for expense group id %s / workspace id %s \n Error: %s',
            expense_id, workspace_id, error
        )


def create_bill(expense_group, task_log):
    try:
        with transaction.atomic():
            __validate_expense_group(expense_group)

            bill_object = Bill.create_bill(expense_group)

            bill_lineitems_objects = BillLineitem.create_bill_lineitems(expense_group)

            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)

            netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)

            attachment_links = {}

            for expense_id in expense_group.expenses.values_list('expense_id', flat=True):
                attachment_link = load_attachments(netsuite_connection, expense_id, expense_group)

                if attachment_link:
                    attachment_links[expense_id] = attachment_link

            created_bill = netsuite_connection.post_bill(bill_object, bill_lineitems_objects, attachment_links)

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

    except NetSuiteRequestError as exception:
        all_details = []
        logger.exception(exception)
        detail = json.dumps(exception.__dict__)
        detail = json.loads(detail)
        task_log.status = 'FAILED'

        all_details.append({
            'expense_group_id': expense_group.id,
            'value': 'NetSuite System Error',
            'type': detail['code'],
            'message': detail['message']
        })
        task_log.detail = all_details

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


def create_expense_report(expense_group, task_log):
    try:
        with transaction.atomic():
            __validate_expense_group(expense_group)

            expense_report_object = ExpenseReport.create_expense_report(expense_group)

            expense_report_lineitems_objects = ExpenseReportLineItem.create_expense_report_lineitems(expense_group)

            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)

            netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)

            attachment_links = {}

            for expense_id in expense_group.expenses.values_list('expense_id', flat=True):
                attachment_link = load_attachments(netsuite_connection, expense_id, expense_group)

                if attachment_link:
                    attachment_links[expense_id] = attachment_link

            created_expense_report = netsuite_connection.post_expense_report(
                expense_report_object, expense_report_lineitems_objects, attachment_links
            )

            task_log.detail = created_expense_report
            task_log.expense_report = expense_report_object
            task_log.status = 'COMPLETE'

            task_log.save(update_fields=['detail', 'expense_report', 'status'])

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

    except NetSuiteRequestError as exception:
        all_details = []
        logger.exception(exception)
        detail = json.dumps(exception.__dict__)
        detail = json.loads(detail)
        task_log.status = 'FAILED'

        all_details.append({
            'expense_group_id': expense_group.id,
            'value': 'NetSuite System Error',
            'type': detail['code'],
            'message': detail['message']
        })
        task_log.detail = all_details

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


def create_journal_entry(expense_group, task_log):
    try:
        with transaction.atomic():
            __validate_expense_group(expense_group)

            journal_entry_object = JournalEntry.create_journal_entry(expense_group)

            journal_entry_lineitems_objects = JournalEntryLineItem.create_journal_entry_lineitems(expense_group)

            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)

            netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)

            attachment_links = {}

            for expense_id in expense_group.expenses.values_list('expense_id', flat=True):
                attachment_link = load_attachments(netsuite_connection, expense_id, expense_group)

                if attachment_link:
                    attachment_links[expense_id] = attachment_link

            created_journal_entry = netsuite_connection.post_journal_entry(
                journal_entry_object, journal_entry_lineitems_objects, attachment_links
            )

            task_log.detail = created_journal_entry
            task_log.journal_entry = journal_entry_object
            task_log.status = 'COMPLETE'

            task_log.save(update_fields=['detail', 'journal_entry', 'status'])

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

    except NetSuiteRequestError as exception:
        all_details = []
        logger.exception(exception)
        detail = json.dumps(exception.__dict__)
        detail = json.loads(detail)
        task_log.status = 'FAILED'

        all_details.append({
            'expense_group_id': expense_group.id,
            'value': 'NetSuite System Error',
            'type': detail['code'],
            'message': detail['message']
        })
        task_log.detail = all_details

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

    general_mapping = None
    try:
        general_mapping = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
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

    general_settings: WorkspaceGeneralSettings = WorkspaceGeneralSettings.objects.get(
        workspace_id=expense_group.workspace_id)

    if general_settings.corporate_credit_card_expenses_object and \
            general_settings.corporate_credit_card_expenses_object == 'BILL' and \
            expense_group.fund_source == 'CCC':
        if general_mapping:
            if not (general_mapping.default_ccc_vendor_id or general_mapping.default_ccc_vendor_name):
                bulk_errors.append({
                    'row': None,
                    'expense_group_id': expense_group.id,
                    'value': expense_group.description.get('employee_email'),
                    'type': 'General Mapping',
                    'message': 'Default Credit Card Vendor not found'
                })
    else:
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

        error_message = 'Category Mapping Not Found'
        if expense_group.fund_source == 'CCC':
            account = Mapping.objects.filter(
                source_type='CATEGORY',
                source__value=category,
                destination_type='CCC_ACCOUNT',
                workspace_id=expense_group.workspace_id
            ).first()

            error_message = 'Credit Card Expense Category Mapping Not Found'
        else:
            account = Mapping.objects.filter(
                source_type='CATEGORY',
                source__value=category,
                destination_type='ACCOUNT',
                workspace_id=expense_group.workspace_id
            ).first()

        if not account:
            bulk_errors.append({
                'row': row,
                'expense_group_id': expense_group.id,
                'value': category,
                'type': 'Category Mapping',
                'message': error_message
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
        try:
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

        except FyleSDKError as e:
            task_log.status = 'FATAL'
            logger.error(e.response)
            task_log.detail = e.response

        task_log.save()


def schedule_expense_reports_creation(workspace_id: int, expense_group_ids: List[str], user):
    """
    Schedule expense reports creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :param user: user email
    :return: None
    """
    if expense_group_ids:
        expense_groups = ExpenseGroup.objects.filter(
            workspace_id=workspace_id, id__in=expense_group_ids, expensereport__id__isnull=True
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
                'type': 'CREATING_EXPENSE_REPORT'
            }
        )
        try:
            created_job = jobs.trigger_now(
                callback_url='{0}{1}'.format(
                    settings.API_URL, '/workspaces/{0}/netsuite/expense_reports/'.format(workspace_id)
                ),
                callback_method='POST', object_id=task_log.id, payload={
                    'expense_group_id': expense_group.id,
                    'task_log_id': task_log.id
                }, job_description='Create Expense Report: Workspace id - {0}, user - {1}, expense group id - {2}'.format(
                    workspace_id, user, expense_group.id
                ),
                org_user_id=user_profile['id']
            )
            task_log.task_id = created_job['id']

        except FyleSDKError as e:
            task_log.status = 'FATAL'
            logger.error(e.response)
            task_log.detail = e.response

        task_log.save()


def schedule_journal_entry_creation(workspace_id: int, expense_group_ids: List[str], user):
    """
    Schedule journal entries creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :param user: user email
    :return: None
    """
    if expense_group_ids:
        expense_groups = ExpenseGroup.objects.filter(
            workspace_id=workspace_id, id__in=expense_group_ids, journalentry__id__isnull=True
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
                    'type': 'CREATING_JOURNAL_ENTRY'
                }
            )
            try:
                created_job = jobs.trigger_now(
                    callback_url='{0}{1}'.format(settings.API_URL, '/workspaces/{0}/netsuite/journal_entries/'.format(
                        workspace_id
                    )),
                    callback_method='POST', object_id=task_log.id, payload={
                        'expense_group_id': expense_group.id,
                        'task_log_id': task_log.id
                    },
                    job_description='Create Journal Entry: Workspace id - {0}, user - {1}, expense group id - {2}'.format(
                        workspace_id, user, expense_group.id
                    ),
                    org_user_id=user_profile['id']
                )
                task_log.task_id = created_job['id']

            except FyleSDKError as e:
                task_log.status = 'FATAL'
                logger.error(e.response)
                task_log.detail = e.response

            task_log.save()
