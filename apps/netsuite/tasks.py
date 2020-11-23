import json
import logging
import traceback
from typing import List
import base64
from datetime import datetime

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

from .models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem, JournalEntry, JournalEntryLineItem,\
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
                }
            )

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


def create_vendor_payment(workspace_id):
    try:
        with transaction.atomic():

            fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)

            fyle_connector = FyleConnector(fyle_credentials.refresh_token, workspace_id)

            fyle_connector.sync_reimbursements()

            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

            netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id)

            bills = Bill.objects.filter(payment_synced=False, expense_group__workspace_id=workspace_id).all()

            expense_reports = ExpenseReport.objects.filter(
                payment_synced=False, expense_group__workspace_id=workspace_id
            ).all()

            journal_entries = JournalEntry.objects.filter(
                payment_synced=False, expense_group__workspace_id=workspace_id
            ).all()

            if bills:
                try:
                    task_log = TaskLog.objects.create(
                        workspace_id=workspace_id,
                        type='CREATING_VENDOR_PAYMENT_FOR_BILL',
                        status='IN_PROGRESS'
                    )
                    for bill in bills:
                        line_items = BillLineitem.objects.filter(bill_id=bill.id)

                        all_expenses_paid = True

                        for line_item in line_items:
                            expense = Expense.objects.get(id=line_item.expense.id)
                            reimbursement = Reimbursement.objects.filter(settlement_id=expense.settlement_id).first()

                            if not reimbursement:
                                all_expenses_paid = False
                                break

                            if reimbursement.state != 'COMPLETE':
                                all_expenses_paid = False

                    if all_expenses_paid:
                        bill_task_log = TaskLog.objects.get(expense_group=bill.expense_group)

                        detail = bill_task_log.detail

                        vendor_payment_object = VendorPayment.create_vendor_payment(
                            bill.expense_group, bill.subsidiary_id, bill.vendor_id, bill.currency, bill.memo,
                            bill.external_id, bill.accounts_payable_id, bill.location_id)

                        vendor_payment_lineitems = VendorPaymentLineitem.create_vendor_payment_lineitems(
                            detail['internalId']
                        )

                        created_vendor_payment = netsuite_connection.post_vendor_payment(
                            vendor_payment_object, vendor_payment_lineitems
                        )

                        task_log.expense_group_id = bill.expense_group
                        task_log.detail = created_vendor_payment
                        task_log.vendor_payment = vendor_payment_object
                        task_log.status = 'COMPLETE'

                        bill.payment_synced = True
                        bill.save(update_fields=['payment_synced'])

                        task_log.save(update_fields=['detail', 'vendor_payment', 'status'])

                except NetSuiteCredentials.DoesNotExist:
                    logger.exception(
                        'NetSuite Credentials not found for workspace_id %s / expense group %s',
                        bill.expense_group,
                        workspace_id
                    )
                    detail = {
                        'expense_group_id': bill.expense_group,
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
                        'expense_group_id': bill.expense_group,
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

            if expense_reports:
                try:
                    task_log = TaskLog.objects.create(
                        workspace_id=workspace_id,
                        type='CREATING_VENDOR_PAYMENT_FOR_EXPENSE_REPORT',
                        status='IN_PROGRESS'
                    )
                    for expense_report in expense_reports:
                        line_items = ExpenseReportLineItem.objects.filter(expense_report_id=expense_report.id)

                        all_expenses_paid = True

                        for line_item in line_items:
                            expense = Expense.objects.get(id=line_item.expense.id)
                            reimbursement = Reimbursement.objects.filter(settlement_id=expense.settlement_id).first()

                            if not reimbursement:
                                all_expenses_paid = False
                                break

                            if reimbursement.state != 'COMPLETE':
                                all_expenses_paid = False

                    if all_expenses_paid:
                        expense_report_task_log = TaskLog.objects.get(expense_group=expense_report.expense_group)

                        detail = expense_report_task_log.detail

                        vendor_payment_object = VendorPayment.create_vendor_payment(
                            expense_report.expense_group, expense_report.subsidiary_id, expense_report.entity_id,
                            '', expense_report.memo,
                            expense_report.external_id, expense_report.account_id)

                        vendor_payment_lineitems = VendorPaymentLineitem.create_vendor_payment_lineitems(
                            detail['internalId']
                        )

                        created_vendor_payment = netsuite_connection.post_vendor_payment(
                            vendor_payment_object, vendor_payment_lineitems
                        )

                        task_log.expense_group_id = expense_report.expense_group
                        task_log.detail = created_vendor_payment
                        task_log.vendor_payment = vendor_payment_object
                        task_log.status = 'COMPLETE'

                        expense_report.payment_synced = True
                        expense_report.save(update_fields=['payment_synced'])

                        task_log.save(update_fields=['detail', 'vendor_payment', 'status'])

                except NetSuiteCredentials.DoesNotExist:
                    logger.exception(
                        'NetSuite Credentials not found for workspace_id %s / expense group %s',
                        bill.expense_group,
                        workspace_id
                    )
                    detail = {
                        'expense_group_id': bill.expense_group,
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
                        'expense_group_id': bill.expense_group,
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

            if journal_entries:
                try:
                    task_log = TaskLog.objects.create(
                        workspace_id=workspace_id,
                        type='CREATING_VENDOR_PAYMENT_FOR_JOURNAL_ENTRY',
                        status='IN_PROGRESS'
                    )
                    for journal_entry in journal_entries:
                        line_items = JournalEntryLineItem.objects.filter(journal_entry_id=journal_entry.id)

                        all_expenses_paid = True

                        for line_item in line_items:
                            expense = Expense.objects.get(id=line_item.expense.id)
                            reimbursement = Reimbursement.objects.filter(settlement_id=expense.settlement_id).first()
                            account = line_item.account_id

                            if not reimbursement:
                                all_expenses_paid = False
                                break

                            if reimbursement.state != 'COMPLETE':
                                all_expenses_paid = False

                        if all_expenses_paid:
                            journal_task_log = TaskLog.objects.get(expense_group=journal_entry.expense_group)

                            detail = journal_task_log.detail
                            vendor_payment_object = VendorPayment.create_vendor_payment(
                                journal_entry.expense_group, journal_entry.subsidiary_id, line_item.entity_id,
                                journal_entry.currency, journal_entry.memo, journal_entry.external_id, account)

                            vendor_payment_lineitems = VendorPaymentLineitem.create_vendor_payment_lineitems(
                                detail['internalId']
                            )

                            created_vendor_payment = netsuite_connection.post_vendor_payment(
                                vendor_payment_object, vendor_payment_lineitems
                            )

                            task_log.expense_group_id = journal_entry.expense_group
                            task_log.detail = created_vendor_payment
                            task_log.vendor_payment = vendor_payment_object
                            task_log.status = 'COMPLETE'

                            journal_entry.payment_synced = True
                            journal_entry.save(update_fields=['payment_synced'])

                            task_log.save(update_fields=['detail', 'vendor_payment', 'status'])

                except NetSuiteCredentials.DoesNotExist:
                    logger.exception(
                        'NetSuite Credentials not found for workspace_id %s / expense group %s',
                        bill.expense_group,
                        workspace_id
                    )
                    detail = {
                        'expense_group_id': bill.expense_group,
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
                        'expense_group_id': bill.expense_group,
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
        logger.exception('Something unexpected happened workspace_id: %s %s', workspace_id, error)


def schedule_vendor_payment_creation(sync_payments, workspace_id):
    if sync_payments:
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
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.netsuite.tasks.create_vendor_payment',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()
