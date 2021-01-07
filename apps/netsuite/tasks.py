import json
import logging
import traceback
from typing import List
import base64
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django_q.models import Schedule
from django_q.tasks import Chain

from netsuitesdk.internal.exceptions import NetSuiteRequestError

from fyle_accounting_mappings.models import Mapping

from fyle_netsuite_api.exceptions import BulkError

from apps.fyle.utils import FyleConnector
from apps.fyle.models import ExpenseGroup, Expense, Reimbursement
from apps.mappings.models import GeneralMapping, SubsidiaryMapping
from apps.tasks.models import TaskLog
from apps.workspaces.models import NetSuiteCredentials, FyleCredential, WorkspaceGeneralSettings

from .models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem, JournalEntry, JournalEntryLineItem, \
    VendorPayment, VendorPaymentLineitem
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
            "externalId": '{}-{}-{}'.format(
                workspace_id, expense_group.id, expense_group.description['employee_email']
            ),
            "name": '{}-{}-{}'.format(workspace_id, expense_group.id, expense_group.description['employee_email'])
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
            })
            file = netsuite_connection.connection.files.get(externalId=expense_id)
            return file['url']
    except Exception:
        error = traceback.format_exc()
        logger.error(
            'Attachment failed for expense group id %s / workspace id %s Error: %s',
            expense_id, workspace_id, {'error': error}
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

            expense_group.exported_at = datetime.now()
            expense_group.save()

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
        logger.exception({'error': exception})
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
        logger.exception('Something unexpected happened workspace_id: %s %s', task_log.workspace_id, task_log.detail)


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

            expense_group.exported_at = datetime.now()
            expense_group.save()

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
        logger.exception({'error': exception})
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
        logger.exception('Something unexpected happened workspace_id: %s %s', task_log.workspace_id, task_log.detail)


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

            expense_group.exported_at = datetime.now()
            expense_group.save()

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
        logger.exception({'error': exception})
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
        logger.exception('Something unexpected happened workspace_id: %s %s', task_log.workspace_id, task_log.detail)


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

        if lineitem.billable and general_settings.import_projects:
            project = Mapping.objects.filter(
                source_type='PROJECT',
                source__value=lineitem.project,
                destination_type='PROJECT',
                workspace_id=expense_group.workspace_id
            ).first()

            if not project:
                bulk_errors.append({
                    'row': row,
                    'expense_group_id': expense_group.id,
                    'value': lineitem.project,
                    'type': 'Project Mapping',
                    'message': 'Project mapping not found'
                })

        row = row + 1

    if bulk_errors:
        raise BulkError('Mappings are missing', bulk_errors)


def schedule_bills_creation(workspace_id: int, expense_group_ids: List[str]):
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

    chain = Chain(cached=True)

    for expense_group in expense_groups:
        task_log, _ = TaskLog.objects.update_or_create(
            workspace_id=expense_group.workspace_id,
            expense_group=expense_group,
            defaults={
                'status': 'IN_PROGRESS',
                'type': 'CREATING_BILL'
            }
        )

        chain.append('apps.netsuite.tasks.create_bill', expense_group, task_log)

        task_log.save()
    if chain.length():
        chain.run()


def schedule_expense_reports_creation(workspace_id: int, expense_group_ids: List[str]):
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

    chain = Chain(cached=True)

    for expense_group in expense_groups:
        task_log, _ = TaskLog.objects.update_or_create(
            workspace_id=expense_group.workspace_id,
            expense_group=expense_group,
            defaults={
                'status': 'IN_PROGRESS',
                'type': 'CREATING_EXPENSE_REPORT'
            }
        )

        chain.append('apps.netsuite.tasks.create_expense_report', expense_group, task_log)
        task_log.save()
    if chain.length():
        chain.run()


def schedule_journal_entry_creation(workspace_id: int, expense_group_ids: List[str]):
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

    chain = Chain(cached=True)

    for expense_group in expense_groups:
        task_log, _ = TaskLog.objects.update_or_create(
            workspace_id=expense_group.workspace_id,
            expense_group=expense_group,
            defaults={
                'status': 'IN_PROGRESS',
                'type': 'CREATING_JOURNAL_ENTRY'
            }
        )

        chain.append('apps.netsuite.tasks.create_journal_entry', expense_group, task_log)
        task_log.save()
    if chain.length():
        chain.run()


def check_expenses_reimbursement_status(expenses):
    all_expenses_paid = True

    for expense in expenses:
        reimbursement = Reimbursement.objects.filter(settlement_id=expense.settlement_id).first()

        if reimbursement.state != 'COMPLETE':
            all_expenses_paid = False

    return all_expenses_paid


def create_netsuite_payment_objects(netsuite_objects, object_type, workspace_id):
    netsuite_payment_objects = {}

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

    netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id)

    for netsuite_object in netsuite_objects:
        entity_id = netsuite_object.entity_id

        expense_group_reimbursement_status = check_expenses_reimbursement_status(
            netsuite_object.expense_group.expenses.all())

        netsuite_object_task_log = TaskLog.objects.get(expense_group=netsuite_object.expense_group)

        if object_type == 'BILL':
            netsuite_entry = netsuite_connection.get_bill(netsuite_object_task_log.detail['internalId'])
        else:
            netsuite_entry = netsuite_connection.get_expense_report(netsuite_object_task_log.detail['internalId'])

        if netsuite_entry['status'] != 'Paid In Full':
            if expense_group_reimbursement_status:
                if entity_id not in netsuite_payment_objects:
                    netsuite_payment_objects[entity_id] = {
                        'subsidiary_id': netsuite_object.subsidiary_id,
                        'entity_id': entity_id,
                        'currency': netsuite_object.currency,
                        'memo': 'Payment for {0} by {1}'.format(
                            object_type.lower(), netsuite_object.expense_group.description['employee_email']
                        ),
                        'unique_id': '{0}-{1}'.format(netsuite_object.external_id, netsuite_object.id),
                        'line': [
                            {
                                'internal_id': netsuite_object_task_log.detail['internalId'],
                                'entity_id': entity_id,
                                'expense_group': netsuite_object.expense_group,
                            }
                        ]
                    }
                else:
                    netsuite_payment_objects[entity_id]['line'].append(
                        {
                            'internal_id': netsuite_object_task_log.detail['internalId'],
                            'entity_id': entity_id,
                            'expense_group': netsuite_object.expense_group,
                        }
                    )
        else:
            netsuite_object.payment_synced = True
            netsuite_object.paid_on_netsuite = True
            netsuite_object.save(update_fields=['payment_synced', 'paid_on_netsuite'])

    return netsuite_payment_objects


def process_vendor_payment(entity_object, workspace_id, object_type):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

    netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id)

    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=workspace_id,
        task_id='PAYMENT_{}'.format(entity_object['unique_id']),
        defaults={
            'status': 'IN_PROGRESS',
            'type': 'CREATING_VENDOR_PAYMENT'
        }
    )
    try:
        with transaction.atomic():

            vendor_payment_object = VendorPayment.create_vendor_payment(
                workspace_id, entity_object
            )

            vendor_payment_lineitems = VendorPaymentLineitem.create_vendor_payment_lineitems(
                entity_object['line'], vendor_payment_object
            )

            created_vendor_payment = netsuite_connection.post_vendor_payment(
                vendor_payment_object, vendor_payment_lineitems
            )

            lines = entity_object['line']
            expense_group_ids = [line['expense_group'].id for line in lines]

            if object_type == 'BILL':
                paid_objects = Bill.objects.filter(expense_group_id__in=expense_group_ids).all()

            else:
                paid_objects = ExpenseReport.objects.filter(expense_group_id__in=expense_group_ids).all()

            for paid_object in paid_objects:
                paid_object.payment_synced = True
                paid_object.paid_on_netsuite = True
                paid_object.save(update_fields=['payment_synced', 'paid_on_netsuite'])

            task_log.detail = created_vendor_payment
            task_log.vendor_payment = vendor_payment_object
            task_log.status = 'COMPLETE'

            task_log.save(update_fields=['detail', 'vendor_payment', 'status'])
    except NetSuiteCredentials.DoesNotExist:
        logger.error(
            'NetSuite Credentials not found for workspace_id %s',
            workspace_id
        )
        detail = {
            'message': 'NetSuite Account not connected'
        }
        task_log.status = 'FAILED'
        task_log.detail = detail

        task_log.save(update_fields=['detail', 'status'])

    except NetSuiteRequestError as exception:
        all_details = []
        logger.exception({'error': exception})
        detail = json.dumps(exception.__dict__)
        detail = json.loads(detail)
        task_log.status = 'FAILED'

        all_details.append({
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


def create_vendor_payment(workspace_id):
    try:
        fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)

        fyle_connector = FyleConnector(fyle_credentials.refresh_token, workspace_id)

        fyle_connector.sync_reimbursements()

        bills = Bill.objects.filter(
            payment_synced=False, expense_group__workspace_id=workspace_id, expense_group__fund_source='PERSONAL'
        ).all()

        expense_reports = ExpenseReport.objects.filter(
            payment_synced=False, expense_group__workspace_id=workspace_id, expense_group__fund_source='PERSONAL'
        ).all()

        if bills:
            bill_entity_map = create_netsuite_payment_objects(bills, 'BILL', workspace_id)

            for entity_object_key in bill_entity_map:
                entity_id = entity_object_key
                entity_object = bill_entity_map[entity_id]

                process_vendor_payment(entity_object, workspace_id, 'BILL')

        if expense_reports:
            expense_report_entity_map = create_netsuite_payment_objects(expense_reports, 'EXPENSE REPORT', workspace_id)

            for entity_object_key in expense_report_entity_map:
                entity_id = entity_object_key
                entity_object = expense_report_entity_map[entity_id]

                process_vendor_payment(entity_object, workspace_id, 'EXPENSE REPORT')
    except Exception:
        error = traceback.format_exc()
        logger.exception('Something unexpected happened workspace_id: %s %s', workspace_id, {'error': error})


def schedule_vendor_payment_creation(sync_fyle_to_netsuite_payments, workspace_id):
    general_mappings: GeneralMapping = GeneralMapping.objects.filter(workspace_id=workspace_id).first()
    if general_mappings:
        if sync_fyle_to_netsuite_payments and general_mappings.vendor_payment_account_id:
            start_datetime = datetime.now()
            schedule, _ = Schedule.objects.update_or_create(
                func='apps.netsuite.tasks.create_vendor_payment',
                args='{}'.format(workspace_id),
                defaults={
                    'schedule_type': Schedule.MINUTES,
                    'minutes': 24 * 60,
                    'next_run': start_datetime
                }
            )
    if not sync_fyle_to_netsuite_payments:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.netsuite.tasks.create_vendor_payment',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()


def get_all_internal_ids(netsuite_objects):
    netsuite_objects_details = {}

    expense_group_ids = [netsuite_object.expense_group_id for netsuite_object in netsuite_objects]

    task_logs = TaskLog.objects.filter(expense_group_id__in=expense_group_ids).all()

    for task_log in task_logs:
        netsuite_objects_details[task_log.expense_group.id] = {
            'expense_group': task_log.expense_group,
            'internal_id': task_log.detail['internalId']
        }

    return netsuite_objects_details


def check_netsuite_object_status(workspace_id):
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

    netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id)

    bills = Bill.objects.filter(
        expense_group__workspace_id=workspace_id, paid_on_netsuite=False, expense_group__fund_source='PERSONAL'
    ).all()

    expense_reports = ExpenseReport.objects.filter(
        expense_group__workspace_id=workspace_id, paid_on_netsuite=False, expense_group__fund_source='PERSONAL'
    ).all()

    if bills:
        internal_ids = get_all_internal_ids(bills)

        for bill in bills:
            bill_object = netsuite_connection.get_bill(internal_ids[bill.expense_group.id]['internal_id'])

            if bill_object['status'] == 'Paid In Full':
                line_items = BillLineitem.objects.filter(bill_id=bill.id)
                for line_item in line_items:
                    expense = line_item.expense
                    expense.paid_on_netsuite = True
                    expense.save(update_fields=['paid_on_netsuite'])

                bill.paid_on_netsuite = True
                bill.payment_synced = True
                bill.save(update_fields=['paid_on_netsuite', 'payment_synced'])

    if expense_reports:
        internal_ids = get_all_internal_ids(expense_reports)

        for expense_report in expense_reports:
            expense_report_object = netsuite_connection.get_expense_report(
                internal_ids[expense_report.expense_group.id]['internal_id'])

            if expense_report_object['status'] == 'Paid In Full':
                line_items = ExpenseReportLineItem.objects.filter(expense_report_id=expense_report.id)
                for line_item in line_items:
                    expense = line_item.expense
                    expense.paid_on_netsuite = True
                    expense.save(update_fields=['paid_on_netsuite'])

                expense_report.paid_on_netsuite = True
                expense_report.payment_synced = True
                expense_report.save(update_fields=['paid_on_netsuite', 'payment_synced'])


def schedule_netsuite_objects_status_sync(sync_netsuite_to_fyle_payments, workspace_id):
    if sync_netsuite_to_fyle_payments:
        start_datetime = datetime.now()
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.netsuite.tasks.check_netsuite_object_status',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': start_datetime
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.netsuite.tasks.check_netsuite_object_status',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()


def process_reimbursements(workspace_id):
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)

    fyle_connector = FyleConnector(fyle_credentials.refresh_token, workspace_id)

    fyle_connector.sync_reimbursements()

    reimbursements = Reimbursement.objects.filter(state='PENDING', workspace_id=workspace_id).all()

    reimbursement_ids = []

    if reimbursements:
        for reimbursement in reimbursements:
            expenses = Expense.objects.filter(settlement_id=reimbursement.settlement_id, fund_source='PERSONAL').all()
            paid_expenses = expenses.filter(paid_on_netsuite=True)

            all_expense_paid = False
            if len(expenses):
                all_expense_paid = len(expenses) == len(paid_expenses)

            if all_expense_paid:
                reimbursement_ids.append(reimbursement.reimbursement_id)

    if reimbursement_ids:
        fyle_connector.post_reimbursement(reimbursement_ids)
        fyle_connector.sync_reimbursements()


def schedule_reimbursements_sync(sync_netsuite_to_fyle_payments, workspace_id):
    if sync_netsuite_to_fyle_payments:
        start_datetime = datetime.now() + timedelta(hours=12)
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.netsuite.tasks.process_reimbursements',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': start_datetime
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.netsuite.tasks.process_reimbursements',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()
