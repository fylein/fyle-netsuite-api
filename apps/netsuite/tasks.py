import json
import logging
import traceback
import itertools
from typing import List
import base64
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils.module_loading import import_string
from django_q.models import Schedule
from django_q.tasks import Chain, async_task

from netsuitesdk.internal.exceptions import NetSuiteRequestError
from netsuitesdk import NetSuiteRateLimitError, NetSuiteLoginError

from fyle_accounting_mappings.models import ExpenseAttribute, Mapping, DestinationAttribute, CategoryMapping, EmployeeMapping
from fyle_integrations_platform_connector import PlatformConnector
from fyle.platform.exceptions import InternalServerError, InvalidTokenError

from fyle_netsuite_api.exceptions import BulkError

from apps.fyle.models import ExpenseGroup, Expense, Reimbursement
from apps.mappings.models import GeneralMapping, SubsidiaryMapping
from apps.tasks.models import TaskLog
from apps.workspaces.models import NetSuiteCredentials, FyleCredential, Configuration, Workspace

from .models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem, JournalEntry, JournalEntryLineItem, \
    VendorPayment, VendorPaymentLineitem, CreditCardCharge, CreditCardChargeLineItem
from .connector import NetSuiteConnector

logger = logging.getLogger(__name__)
logger.level = logging.INFO

netsuite_paid_state = 'Paid In Full'
netsuite_error_message = 'NetSuite System Error'

TASK_TYPE_CONSTRUCT_LINE_FUNC_MAP = {
    'CREATING_EXPENSE_REPORT': 'construct_expense_report_lineitems',
    'CREATING_BILL': 'construct_bill_lineitems',
    'CREATING_JOURNAL_ENTRY': 'construct_journal_entry_lineitems',
    'CREATING_CREDIT_CARD_CHARGE': 'construct_credit_card_charge_lineitems'
}

TASK_TYPE_EXPORT_COL_MAP = {
    'CREATING_EXPENSE_REPORT': 'expense_report',
    'CREATING_BILL': 'bill',
    'CREATING_JOURNAL_ENTRY': 'journal_entry',
    'CREATING_CREDIT_CARD_CHARGE': 'credit_card_charge'
}

TASK_TYPE_LINE_ITEM_COL_MAP = {
    'CREATING_EXPENSE_REPORT': 'ExpenseReportLineItem',
    'CREATING_BILL': 'BillLineitem',
    'CREATING_JOURNAL_ENTRY': 'JournalEntryLineItem',
    'CREATING_CREDIT_CARD_CHARGE': 'CreditCardChargeLineItem'
}

TASK_TYPE_EXPORT_MAP = {
    'CREATING_EXPENSE_REPORT': 'expense_reports',
    'CREATING_BILL': 'vendor_bills',
    'CREATING_JOURNAL_ENTRY': 'journal_entries'
}

TASK_TYPE_LINES_MAP = {
    'CREATING_EXPENSE_REPORT': 'expenseList',
    'CREATING_BILL': 'expenseList',
    'CREATING_JOURNAL_ENTRY': 'lineList',
    'CREATING_CREDIT_CARD_CHARGE': 'expenses',
}


def load_attachments(netsuite_connection: NetSuiteConnector, expense: Expense, expense_group: ExpenseGroup):
    """
    Get attachments from Fyle
    :param netsuite_connection: NetSuite Connection
    :param expense_id: Fyle expense id
    :param expense_group: Integration Expense group
    """
    workspace_id = expense_group.workspace_id
    workspace = expense_group.workspace

    try:
        fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
        file_ids = expense.file_ids
        platform = PlatformConnector(fyle_credentials)

        files_list = []
        attachments = []
        receipt_url = None

        if file_ids and len(file_ids):
            folder = netsuite_connection.connection.folders.post({
                "externalId": workspace.fyle_org_id,
                "name": 'Fyle Attachments - {0}'.format(workspace.name)
            })
            files_list = [{'id': file_ids[0]}]
            attachments = platform.files.bulk_generate_file_urls(files_list)

            if attachments:
                for attachment in attachments:
                    netsuite_connection.connection.files.post({
                        "externalId": expense.expense_id,
                        "name": '{0}_{1}'.format(attachment['id'], attachment['name']),
                        'content': base64.b64decode(attachment['download_url']),
                        "folder": {
                            "name": None,
                            "internalId": folder['internalId'],
                            "externalId": folder['externalId'],
                            "type": "folder"
                        }
                    })

                file = netsuite_connection.connection.files.get(externalId=expense.expense_id)
                receipt_url = file['url']

        return receipt_url

    except InvalidTokenError:
        logger.info('Invalid Fyle refresh token for workspace %s', workspace_id)

    except Exception:
        error = traceback.format_exc()
        logger.info(
            'Attachment failed for expense group id %s / workspace id %s Error: %s',
            expense.expense_id, workspace_id, {'error': error}
        )


def get_or_create_credit_card_vendor(expense_group: ExpenseGroup, merchant: str, auto_create_merchants: bool):
    """
    Get or create car default vendor
    :param expense_group: Expense Group
    :param merchant: Fyle Expense Merchant
    :param auto_create_merchants: Create merchant if doesn't exist
    :return:
    """
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)
    netsuite_connection = NetSuiteConnector(
        netsuite_credentials=netsuite_credentials, workspace_id=int(expense_group.workspace_id))

    vendor = netsuite_connection.connection.vendors.search(attribute='entityId', value=merchant, operator='is')

    if not vendor:
        if auto_create_merchants and merchant is not None:
            created_vendor = netsuite_connection.post_vendor(expense_group=expense_group, merchant=merchant)
            return netsuite_connection.create_destination_attribute('vendor', merchant, created_vendor['internalId'])
    else:
        vendor = vendor[0]
        return netsuite_connection.create_destination_attribute(
            'vendor', vendor['entityId'], vendor['internalId'])


def __log_error(task_log: TaskLog) -> None:
    logger.exception('Something unexpected happened workspace_id: %s %s', task_log.workspace_id, task_log.detail)


def create_or_update_employee_mapping(expense_group: ExpenseGroup, netsuite_connection: NetSuiteConnector,
                                      auto_map_employees_preference: str, employee_field_mapping: str):
    try:
        employee = get_employee_expense_attribute(expense_group.description.get('employee_email'), expense_group.workspace_id)
        if not employee:
            # Sync inactive employee and gracefully handle export failure
            employee = sync_inactive_employee(expense_group)

        mapping = EmployeeMapping.objects.get(
            source_employee=employee,
            workspace_id=expense_group.workspace_id
        )

        mapping = mapping.destination_employee if employee_field_mapping == 'EMPLOYEE' \
            else mapping.destination_vendor

        if not mapping:
            raise EmployeeMapping.DoesNotExist
    except EmployeeMapping.DoesNotExist:
        source_employee = ExpenseAttribute.objects.get(
            workspace_id=expense_group.workspace_id,
            attribute_type='EMPLOYEE',
            value=expense_group.description.get('employee_email')
        )

        try:
            filters = {}
            if auto_map_employees_preference == 'EMAIL':
                filters = {
                    'detail__email__iexact': source_employee.value,
                    'attribute_type': employee_field_mapping
                }
            elif auto_map_employees_preference == 'NAME':
                filters = {
                    'value__iexact': source_employee.detail['full_name'],
                    'attribute_type': employee_field_mapping
                }

            created_entity = DestinationAttribute.objects.filter(
                workspace_id=expense_group.workspace_id,
                **filters
            ).first()

            existing_employee_mapping = EmployeeMapping.objects.filter(
                source_employee=source_employee
            ).first()

            destination = {}
            if employee_field_mapping == 'EMPLOYEE':
                if created_entity is None:
                    created_entity: DestinationAttribute = netsuite_connection.get_or_create_employee(
                        source_employee, expense_group)
                    destination['destination_employee_id'] = created_entity.id
                elif existing_employee_mapping and existing_employee_mapping.destination_employee:
                    destination['destination_employee_id'] = existing_employee_mapping.destination_employee.id
            else:
                if created_entity is None:
                    created_entity: DestinationAttribute = netsuite_connection.get_or_create_vendor(
                        source_employee, expense_group)
                    destination['destination_vendor_id'] = created_entity.id
                elif existing_employee_mapping and existing_employee_mapping.destination_vendor:
                    destination['destination_vendor_id'] = existing_employee_mapping.destination_vendor.id

            if existing_employee_mapping and existing_employee_mapping.destination_card_account:
                destination['destination_card_account_id'] = existing_employee_mapping.destination_card_account.id

            if 'destination_employee_id' not in destination or not destination['destination_employee_id']:
                destination['destination_employee_id'] = created_entity.id

            if 'destination_vendor_id' not in destination or not destination['destination_vendor_id']:
                destination['destination_vendor_id'] = created_entity.id

            mapping = EmployeeMapping.create_or_update_employee_mapping(
                source_employee_id=source_employee.id,
                workspace=expense_group.workspace,
                **destination
            )

            mapping.source_employee.auto_mapped = True
            mapping.source_employee.save()

            if employee_field_mapping == 'EMPLOYEE':
                mapping.destination_employee.auto_created = True
                mapping.destination_employee.save()
            elif employee_field_mapping == 'VENDOR':
                mapping.destination_vendor.auto_created = True
                mapping.destination_vendor.save()

        except NetSuiteRequestError as exception:
            logger.info({'error': exception})


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
    task_log.status = 'FAILED'
    task_log.detail = detail

    task_log.save()

def construct_payload_and_update_export(expense_id_receipt_url_map: dict, task_log: TaskLog, workspace: Workspace,
    cluster_domain: str, netsuite_connection: NetSuiteConnector):
    """
    Construct payload and update export
    :param expense_id_receipt_url_map: expense_id_receipt_url_map ex - {'tx4ziVSAyIsv': 'receipt_url_1', 'tx4ziVSAyIs2': 'receipt_url_2'}
    :param task_log: task_log
    :param workspace: workspace
    :param cluster_domain: cluster_domain
    :param netsuite_connection: netsuite_connection
    :return: None
    """
    if expense_id_receipt_url_map:
        # target function that constructs lines payload, ex - construct_expense_report_lineitems
        func = TASK_TYPE_CONSTRUCT_LINE_FUNC_MAP[task_log.type]

        # this holds the export instance, ex - ExpenseReport / JournalEntry / Bill
        export_instance = getattr(task_log, TASK_TYPE_EXPORT_COL_MAP[task_log.type])

        # this holds the line items filter for a given export instance, ex - {'expense_report_id': 1}
        line_items_filter = {
            '{}_id'.format(TASK_TYPE_EXPORT_COL_MAP[task_log.type]): export_instance.id
        }

        # this holds the line item model, ex - ExpenseReportLineitem / JournalEntryLineitem / BillLineitem
        line_item_model = import_string('apps.netsuite.models.{}'.format(TASK_TYPE_LINE_ITEM_COL_MAP[task_log.type]))
        export_line_items = line_item_model.objects.filter(**line_items_filter)

        lines = []
        expense_list = []
        item_list = []
        payload = {}

        # Since we have credit and debit for Journal Entry lines, we need to construct them separately
        if task_log.type == 'CREATING_JOURNAL_ENTRY':
            construct_lines = getattr(netsuite_connection, func)

            # calling the target construct payload function with credit and debit
            credit_line = construct_lines(export_line_items, credit='Credit', org_id=workspace.fyle_org_id)
            debit_line = construct_lines(
                export_line_items, debit='Debit', attachment_links=expense_id_receipt_url_map,
                cluster_domain=cluster_domain, org_id=workspace.fyle_org_id
            )
            lines.extend(credit_line)
            lines.extend(debit_line)

        elif task_log.type == 'CREATING_BILL':
            construct_lines = getattr(netsuite_connection, func)
            # calling the target construct payload function
            expense_list, item_list = construct_lines(export_line_items, expense_id_receipt_url_map, cluster_domain, workspace.fyle_org_id)
        else:
            construct_lines = getattr(netsuite_connection, func)
            # calling the target construct payload function
            lines = construct_lines(export_line_items, expense_id_receipt_url_map, cluster_domain, workspace.fyle_org_id)

        # final payload to be sent to netsuite, since this is an update operation, we need to pass the external id
        if task_log.type == 'CREATING_BILL':
            payload = {
                TASK_TYPE_LINES_MAP[task_log.type]: expense_list,
                'itemList': item_list,
                'externalId': export_instance.external_id
            }
        else:
            payload = {
                TASK_TYPE_LINES_MAP[task_log.type]: lines,
                'externalId': export_instance.external_id
            }

        # calling the target netsuite post function, ex - netsuite_connection.connection.expense_reports.post(payload)
        getattr(netsuite_connection.connection, TASK_TYPE_EXPORT_MAP[task_log.type]).post(payload)

        # Update netsuite_receipt_url in line_items table
        for line_item in export_line_items:
            line_item.netsuite_receipt_url = expense_id_receipt_url_map.get(line_item.expense.expense_id, None)
            line_item.save()


def upload_attachments_and_update_export(expenses: List[Expense], task_log: TaskLog, fyle_credentials: FyleCredential, workspace_id: int):
    """
    Upload attachments and update export
    :param expenses: list of expenses
    :param task_log: task_log
    :param fyle_credentials: fyle_credentials
    :param workspace_id: workspace_id
    :return: None
    """
    try:
        netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
        netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id)
        workspace = netsuite_credentials.workspace

        platform = PlatformConnector(fyle_credentials=fyle_credentials)

        expense_id_receipt_url_map = {}

        for expense in expenses:
            if expense.file_ids and len(expense.file_ids):
                # Grabbing 1st attachment since we can upload only 1 attachment per expense
                payload = [{'id': expense.file_ids[0]}]
                attachments = platform.files.bulk_generate_file_urls(payload)

                attachment = attachments[0] if len(attachments) else None

                if attachment:
                    netsuite_connection.connection.files.post({
                        'externalId': expense.expense_id,
                        'name': '{0}_{1}'.format(attachment['id'], attachment['name']),
                        'content': base64.b64decode(attachment['download_url']),
                        'folder': {
                            'name': None,
                            'internalId': None,
                            'externalId': workspace.fyle_org_id,
                            'type': 'folder'
                        }
                    })

                    file = netsuite_connection.connection.files.get(externalId=expense.expense_id)
                    receipt_url = file['url']
                    expense_id_receipt_url_map[expense.expense_id] = receipt_url

        construct_payload_and_update_export(expense_id_receipt_url_map, task_log, workspace, fyle_credentials.cluster_domain, netsuite_connection)

    except (NetSuiteRateLimitError, NetSuiteRequestError, NetSuiteLoginError, InvalidTokenError) as exception:
        logger.info('Error while uploading attachments to netsuite workspace_id - %s %s', workspace_id, exception.__dict__)

    except Exception as exception:
        logger.error(
            'Error while uploading attachments to netsuite workspace_id - %s %s %s',
            workspace_id, exception, traceback.format_exc()
        )


def create_bill(expense_group, task_log_id):
    task_log = TaskLog.objects.get(id=task_log_id)

    if task_log.status not in ['IN_PROGRESS', 'COMPLETE']:
        task_log.status = 'IN_PROGRESS'
        task_log.save()
    else:
        return

    configuration: Configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)
    general_mappings: GeneralMapping = GeneralMapping.objects.filter(workspace_id=expense_group.workspace_id).first()

    try:
        fyle_credentials = FyleCredential.objects.get(workspace_id=expense_group.workspace_id)
        netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)

        netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)

        if expense_group.fund_source == 'PERSONAL' and configuration.auto_map_employees \
                and configuration.auto_create_destination_entity:
            create_or_update_employee_mapping(
                expense_group, netsuite_connection, configuration.auto_map_employees,
                configuration.employee_field_mapping)

        if general_mappings and general_mappings.use_employee_department and expense_group.fund_source == 'CCC' \
                and configuration.auto_map_employees and configuration.auto_create_destination_entity:
            create_or_update_employee_mapping(
                expense_group, netsuite_connection, configuration.auto_map_employees,
                configuration.employee_field_mapping)

        __validate_expense_group(expense_group, configuration)
        with transaction.atomic():
            bill_object = Bill.create_bill(expense_group)

            bill_lineitems_objects = BillLineitem.create_bill_lineitems(expense_group, configuration)

            created_bill = netsuite_connection.post_bill(bill_object, bill_lineitems_objects)

            task_log.detail = created_bill
            task_log.bill = bill_object
            task_log.status = 'COMPLETE'

            task_log.save()

            expense_group.exported_at = datetime.now()
            expense_group.response_logs = created_bill
            expense_group.save()

            async_task(
                'apps.netsuite.tasks.upload_attachments_and_update_export',
                expense_group.expenses.all(), task_log, fyle_credentials, expense_group.workspace_id
            )

    except NetSuiteCredentials.DoesNotExist:
        __handle_netsuite_connection_error(expense_group, task_log)

    except (NetSuiteRequestError, NetSuiteLoginError) as exception:
        all_details = []
        logger.info({'error': exception})
        detail = json.dumps(exception.__dict__)
        detail = json.loads(detail)
        task_log.status = 'FAILED'

        all_details.append({
            'expense_group_id': expense_group.id,
            'value': netsuite_error_message,
            'type': detail['code'],
            'message': detail['message']
        })
        task_log.detail = all_details

        task_log.save()

    except BulkError as exception:
        logger.info(exception.response)
        detail = exception.response
        task_log.status = 'FAILED'
        task_log.detail = detail

        task_log.save()

    except NetSuiteRateLimitError:
        logger.info('Rate limit error, workspace_id - %s', expense_group.workspace_id)
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


def create_credit_card_charge(expense_group, task_log_id):
    task_log = TaskLog.objects.get(id=task_log_id)

    if task_log.status not in ['IN_PROGRESS', 'COMPLETE']:
        task_log.status = 'IN_PROGRESS'
        task_log.save()
    else:
        return

    configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)
    general_mappings: GeneralMapping = GeneralMapping.objects.filter(workspace_id=expense_group.workspace_id).first()

    try:
        netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)

        netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)

        if general_mappings and general_mappings.use_employee_department and expense_group.fund_source == 'CCC' \
                and configuration.auto_map_employees and configuration.auto_create_destination_entity:
            create_or_update_employee_mapping(
                expense_group, netsuite_connection, configuration.auto_map_employees,
                configuration.employee_field_mapping)

        merchant = expense_group.expenses.first().vendor
        auto_create_merchants = configuration.auto_create_merchants
        get_or_create_credit_card_vendor(expense_group, merchant, auto_create_merchants)

        __validate_expense_group(expense_group, configuration)
        with transaction.atomic():
            credit_card_charge_object = CreditCardCharge.create_credit_card_charge(expense_group)

            credit_card_charge_lineitems_object = CreditCardChargeLineItem.create_credit_card_charge_lineitem(
                expense_group, configuration
            )
            attachment_links = {}

            expense = expense_group.expenses.first()
            refund = False
            if expense.amount < 0:
                refund = True

            attachment_link = load_attachments(netsuite_connection, expense, expense_group)

            if attachment_link:
                attachment_links[expense.expense_id] = attachment_link

            created_credit_card_charge = netsuite_connection.post_credit_card_charge(
                credit_card_charge_object, credit_card_charge_lineitems_object, attachment_links, refund
            )

            if refund:
                created_credit_card_charge['type'] = 'chargeCardRefund'
            else:
                created_credit_card_charge['type'] = 'chargeCard'

            task_log.detail = created_credit_card_charge
            task_log.credit_card_charge = credit_card_charge_object
            task_log.status = 'COMPLETE'

            task_log.save()

            expense_group.exported_at = datetime.now()
            expense_group.response_logs = created_credit_card_charge
            expense_group.save()

    except NetSuiteCredentials.DoesNotExist:
        __handle_netsuite_connection_error(expense_group, task_log)

    except (NetSuiteRequestError, NetSuiteLoginError) as exception:
        all_details = []
        logger.info({'error': exception})
        detail = json.dumps(exception.__dict__)
        detail = json.loads(detail)
        task_log.status = 'FAILED'

        all_details.append({
            'expense_group_id': expense_group.id,
            'value': netsuite_error_message,
            'type': detail['code'],
            'message': detail['message']
        })
        task_log.detail = all_details

        task_log.save()

    except BulkError as exception:
        logger.info(exception.response)
        detail = exception.response
        task_log.status = 'FAILED'
        task_log.detail = detail

        task_log.save()

    except NetSuiteRateLimitError:
        logger.info('Rate limit error, workspace_id - %s', expense_group.workspace_id)
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


def create_expense_report(expense_group, task_log_id):
    task_log = TaskLog.objects.get(id=task_log_id)

    if task_log.status not in ['IN_PROGRESS', 'COMPLETE']:
        task_log.status = 'IN_PROGRESS'
        task_log.save()
    else:
        return

    configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)

    try:
        fyle_credentials = FyleCredential.objects.get(workspace_id=expense_group.workspace_id)
        netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)
        netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)

        if configuration.auto_map_employees and configuration.auto_create_destination_entity:
            create_or_update_employee_mapping(
                expense_group, netsuite_connection, configuration.auto_map_employees,
                configuration.employee_field_mapping)

        __validate_expense_group(expense_group, configuration)
        with transaction.atomic():
            expense_report_object = ExpenseReport.create_expense_report(expense_group)

            expense_report_lineitems_objects = ExpenseReportLineItem.create_expense_report_lineitems(
                expense_group, configuration
            )

            created_expense_report = netsuite_connection.post_expense_report(
                expense_report_object, expense_report_lineitems_objects
            )

            task_log.detail = created_expense_report
            task_log.expense_report = expense_report_object
            task_log.status = 'COMPLETE'

            task_log.save()

            expense_group.exported_at = datetime.now()
            expense_group.response_logs = created_expense_report
            expense_group.save()

            async_task(
                'apps.netsuite.tasks.upload_attachments_and_update_export',
                expense_group.expenses.all(), task_log, fyle_credentials, expense_group.workspace_id
            )

    except NetSuiteCredentials.DoesNotExist:
        __handle_netsuite_connection_error(expense_group, task_log)

    except (NetSuiteRequestError, NetSuiteLoginError) as exception:
        all_details = []
        logger.info({'error': exception})
        detail = json.dumps(exception.__dict__)
        detail = json.loads(detail)
        task_log.status = 'FAILED'

        all_details.append({
            'expense_group_id': expense_group.id,
            'value': netsuite_error_message,
            'type': detail['code'],
            'message': detail['message']
        })
        task_log.detail = all_details

        task_log.save()

    except BulkError as exception:
        logger.info(exception.response)
        detail = exception.response
        task_log.status = 'FAILED'
        task_log.detail = detail

        task_log.save()

    except NetSuiteRateLimitError:
        logger.info('Rate limit error, workspace_id - %s', expense_group.workspace_id)
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


def create_journal_entry(expense_group, task_log_id):
    task_log = TaskLog.objects.get(id=task_log_id)

    if task_log.status not in ['IN_PROGRESS', 'COMPLETE']:
        task_log.status = 'IN_PROGRESS'
        task_log.save()
    else:
        return

    configuration = Configuration.objects.get(workspace_id=expense_group.workspace_id)

    try:
        fyle_credentials = FyleCredential.objects.get(workspace_id=expense_group.workspace_id)
        netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)

        netsuite_connection = NetSuiteConnector(netsuite_credentials, expense_group.workspace_id)

        if configuration.auto_map_employees and configuration.auto_create_destination_entity:
            create_or_update_employee_mapping(
                expense_group, netsuite_connection, configuration.auto_map_employees,
                configuration.employee_field_mapping)
        __validate_expense_group(expense_group, configuration)
        with transaction.atomic():
            journal_entry_object = JournalEntry.create_journal_entry(expense_group)

            journal_entry_lineitems_objects = JournalEntryLineItem.create_journal_entry_lineitems(
                expense_group, configuration
            )

            created_journal_entry = netsuite_connection.post_journal_entry(
                journal_entry_object, journal_entry_lineitems_objects
            )

            task_log.detail = created_journal_entry
            task_log.journal_entry = journal_entry_object
            task_log.status = 'COMPLETE'

            task_log.save()

            expense_group.exported_at = datetime.now()
            expense_group.response_logs = created_journal_entry
            expense_group.save()

            async_task(
                'apps.netsuite.tasks.upload_attachments_and_update_export',
                expense_group.expenses.all(), task_log, fyle_credentials, expense_group.workspace_id
            )

    except NetSuiteCredentials.DoesNotExist:
        __handle_netsuite_connection_error(expense_group, task_log)

    except (NetSuiteRequestError, NetSuiteLoginError) as exception:
        all_details = []
        logger.info({'error': exception})
        detail = json.dumps(exception.__dict__)
        detail = json.loads(detail)
        task_log.status = 'FAILED'

        all_details.append({
            'expense_group_id': expense_group.id,
            'value': netsuite_error_message,
            'type': detail['code'],
            'message': detail['message']
        })
        task_log.detail = all_details

        task_log.save()

    except BulkError as exception:
        logger.info(exception.response)
        detail = exception.response
        task_log.status = 'FAILED'
        task_log.detail = detail

        task_log.save()

    except NetSuiteRateLimitError:
        logger.info('Rate limit error, workspace_id - %s', expense_group.workspace_id)
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


def __validate_general_mapping(expense_group: ExpenseGroup, configuration: Configuration) -> List[BulkError]:
    bulk_errors = []
    general_mapping = None
    error_type = 'General Mappings'

    try:
        general_mapping = GeneralMapping.objects.get(workspace_id=expense_group.workspace_id)
    except GeneralMapping.DoesNotExist:
        bulk_errors.append({
            'row': None,
            'expense_group_id': expense_group.id,
            'value': error_type,
            'type': error_type,
            'message': '{} not found'.format(error_type)
        })

    if general_mapping:
        if not (general_mapping.accounts_payable_id or general_mapping.accounts_payable_name) \
            and (
                    (
                    configuration.reimbursable_expenses_object == 'BILL' or \
                        configuration.corporate_credit_card_expenses_object == 'BILL'
                    ) or (
                        configuration.reimbursable_expenses_object == 'JOURNAL ENTRY' and \
                            configuration.employee_field_mapping == 'VENDOR' and \
                                expense_group.fund_source == 'PERSONAL'
                    )
                ):
            bulk_errors.append({
                'row': None,
                'expense_group_id': expense_group.id,
                'value': 'Accounts Payable',
                'type': error_type,
                'message': 'Accounts Payable not found'
            })

        if not (general_mapping.reimbursable_account_id or general_mapping.reimbursable_account_name) \
            and (
                    (
                        configuration.reimbursable_expenses_object == 'EXPENSE REPORT'
                    ) or (
                        configuration.reimbursable_expenses_object == 'JOURNAL ENTRY' and \
                                configuration.employee_field_mapping == 'EMPLOYEE' and \
                                    expense_group.fund_source == 'PERSONAL'
                    )
            ):
            bulk_errors.append({
                'row': None,
                'expense_group_id': expense_group.id,
                'value': 'Reimbursable Account',
                'type': error_type,
                'message': 'Reimbursable Account not found'
            })

        if not (general_mapping.default_ccc_account_id or general_mapping.default_ccc_account_name) and \
            expense_group.fund_source == 'CCC' and \
                configuration.corporate_credit_card_expenses_object in ['CREDIT CARD CHARGE', 'JOURNAL ENTRY']:
            bulk_errors.append({
                'row': None,
                'expense_group_id': expense_group.id,
                'value': 'Default Credit Card Account',
                'type': error_type,
                'message': 'Default Credit Card Account not found'
            })

        if not (general_mapping.default_ccc_vendor_id or general_mapping.default_ccc_vendor_name) and \
            configuration.corporate_credit_card_expenses_object in ['BILL', 'CREDIT CARD CHARGE'] and \
                expense_group.fund_source == 'CCC':
            bulk_errors.append({
                'row': None,
                'expense_group_id': expense_group.id,
                'value': expense_group.description.get('employee_email'),
                'type': error_type,
                'message': 'Default Credit Card Vendor not found'
            })
        
        if not (general_mapping.default_ccc_vendor_id or general_mapping.default_ccc_vendor_name) and \
            expense_group.fund_source == 'CCC' and \
                configuration.corporate_credit_card_expenses_object == 'JOURNAL ENTRY' and configuration.name_in_journal_entry == 'MERCHANT' :
            bulk_errors.append({
                'row': None,
                'expense_group_id': expense_group.id,
                'value': 'Default Journal Entry Vendor',
                'type': error_type,
                'message': 'Default Journal Entry Vendor not found'
            })

    return bulk_errors


def __validate_subsidiary_mapping(expense_group: ExpenseGroup) -> List[BulkError]:
    bulk_errors = []
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

    return bulk_errors


def __validate_tax_group_mapping(expense_group: ExpenseGroup, configuration: Configuration) -> List[BulkError]:
    row = 0
    bulk_errors = []
    expenses = expense_group.expenses.all()

    for lineitem in expenses:
        if configuration.import_tax_items and lineitem.tax_group_id:
            tax_group  = ExpenseAttribute.objects.get(
                workspace_id=expense_group.workspace_id,
                attribute_type='TAX_GROUP',
                source_id=lineitem.tax_group_id
            )

            tax_code = Mapping.objects.filter(
                source_type='TAX_GROUP',
                source__value=tax_group.value,
                workspace_id=expense_group.workspace_id
            ).first()

            if not tax_code:
                bulk_errors.append({
                    'row': row,
                    'expense_group_id': expense_group.id,
                    'value': tax_group.value,
                    'type': 'Tax Group Mapping',
                    'message': 'Tax Group Mapping not found'
                })

        row = row + 1

    return bulk_errors


def get_employee_expense_attribute(value: str, workspace_id: int) -> ExpenseAttribute:
    """
    Get employee expense attribute
    :param value: value
    :param workspace_id: workspace id
    """
    return ExpenseAttribute.objects.filter(
        attribute_type='EMPLOYEE',
        value=value,
        workspace_id=workspace_id
    ).first()

def sync_inactive_employee(expense_group: ExpenseGroup) -> ExpenseAttribute:
    fyle_credentials = FyleCredential.objects.get(workspace_id=expense_group.workspace_id)
    platform = PlatformConnector(fyle_credentials=fyle_credentials)
    fyle_employee = platform.employees.get_employee_by_email(expense_group.description.get('employee_email'))
    if len(fyle_employee):
        fyle_employee = fyle_employee[0]
        attribute = {
            'attribute_type': 'EMPLOYEE',
            'display_name': 'Employee',
            'value': fyle_employee['user']['email'],
            'source_id': fyle_employee['id'],
            'active': True if fyle_employee['is_enabled'] and fyle_employee['has_accepted_invite'] else False,
            'detail': {
                'user_id': fyle_employee['user_id'],
                'employee_code': fyle_employee['code'],
                'full_name': fyle_employee['user']['full_name'],
                'location': fyle_employee['location'],
                'department': fyle_employee['department']['name'] if fyle_employee['department'] else None,
                'department_id': fyle_employee['department_id'],
                'department_code': fyle_employee['department']['code'] if fyle_employee['department'] else None
            }
        }
        ExpenseAttribute.bulk_create_or_update_expense_attributes([attribute], 'EMPLOYEE', expense_group.workspace_id, True)
        return get_employee_expense_attribute(expense_group.description.get('employee_email'), expense_group.workspace_id)

    return None

def __validate_employee_mapping(expense_group: ExpenseGroup, configuration: Configuration) -> List[BulkError]:
    employee = get_employee_expense_attribute(expense_group.description.get('employee_email'), expense_group.workspace_id)

    if not employee:
        # Sync inactive employee and gracefully handle export failure
        employee = sync_inactive_employee(expense_group)

    bulk_errors = []
    if expense_group.fund_source == 'PERSONAL' or configuration.name_in_journal_entry == 'EMPLOYEE' or \
            (expense_group.fund_source == 'CCC' and configuration.corporate_credit_card_expenses_object == 'EXPENSE REPORT'):
        try:
            entity = EmployeeMapping.objects.get(
                source_employee=employee,
                workspace_id=expense_group.workspace_id
            )


            if configuration.employee_field_mapping == 'EMPLOYEE':
                entity = entity.destination_employee
            else:
                entity = entity.destination_vendor

            if not entity:
                raise EmployeeMapping.DoesNotExist
        except EmployeeMapping.DoesNotExist:
            bulk_errors.append({
                'row': None,
                'expense_group_id': expense_group.id,
                'value': expense_group.description.get('employee_email'),
                'type': 'Employee Mapping',
                'message': 'Employee mapping not found'
            })

    return bulk_errors


def __validate_category_mapping(expense_group: ExpenseGroup, configuration: Configuration) -> List[BulkError]:
    row = 0
    bulk_errors = []
    expenses = expense_group.expenses.all()

    for lineitem in expenses:
        category = lineitem.category if (lineitem.category == lineitem.sub_category or lineitem.sub_category == None) else '{0} / {1}'.format(
            lineitem.category, lineitem.sub_category)

        category_mapping = CategoryMapping.objects.filter(
            source_category__value=category,
            workspace_id=expense_group.workspace_id
        ).first()

        if category_mapping:
            if expense_group.fund_source == 'PERSONAL':
                if configuration.reimbursable_expenses_object == 'EXPENSE REPORT':
                    category_mapping = category_mapping.destination_expense_head
                else:
                    category_mapping = category_mapping.destination_account
            else:
                if configuration.corporate_credit_card_expenses_object == 'EXPENSE REPORT':
                    category_mapping = category_mapping.destination_expense_head
                else:
                    category_mapping = category_mapping.destination_account

        if not category_mapping:
            bulk_errors.append({
                'row': row,
                'expense_group_id': expense_group.id,
                'value': category,
                'type': 'Category Mapping',
                'message': 'Category Mapping Not Found'
            })

        row = row + 1

    return bulk_errors


def __validate_expense_group(expense_group: ExpenseGroup, configuration: Configuration):
    # General Mapping
    general_mapping_errors = __validate_general_mapping(expense_group, configuration)

    # Subsidiary Mapping
    subsidiary_mapping_errors = __validate_subsidiary_mapping(expense_group)

    # Employee Mapping
    employee_mapping_errors = __validate_employee_mapping(expense_group, configuration)

    # Category Mapping
    category_mapping_errors = __validate_category_mapping(expense_group, configuration)

    # Tax Group Mapping
    tax_group_mapping_errors = []
    if configuration.import_tax_items:
        tax_group_mapping_errors = __validate_tax_group_mapping(expense_group, configuration)

    bulk_errors = list(
        itertools.chain(
            general_mapping_errors, subsidiary_mapping_errors, employee_mapping_errors, category_mapping_errors, tax_group_mapping_errors
        )
    )

    if bulk_errors:
        raise BulkError('Mappings are missing', bulk_errors)


def schedule_bills_creation(workspace_id: int, expense_group_ids: List[str]):
    """
    Schedule bills creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :return: None
    """
    if expense_group_ids:
        expense_groups = ExpenseGroup.objects.filter(
            Q(tasklog__id__isnull=True) | ~Q(tasklog__status__in=['IN_PROGRESS', 'COMPLETE']),
            workspace_id=workspace_id, id__in=expense_group_ids, bill__id__isnull=True, exported_at__isnull=True
        ).all()

        chain = Chain(cached=False)

        fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
        chain.append('apps.fyle.helpers.sync_dimensions', fyle_credentials, workspace_id)

        for expense_group in expense_groups:
            task_log, _ = TaskLog.objects.get_or_create(
                workspace_id=expense_group.workspace_id,
                expense_group=expense_group,
                defaults={
                    'status': 'ENQUEUED',
                    'type': 'CREATING_BILL'
                }
            )

            if task_log.status not in ['IN_PROGRESS', 'ENQUEUED']:
                task_log.type = 'CREATING_BILL'
                task_log.status = 'ENQUEUED'
                task_log.save()

            chain.append('apps.netsuite.tasks.create_bill', expense_group, task_log.id)

            task_log.save()
        if chain.length() > 1:
            chain.run()


def schedule_credit_card_charge_creation(workspace_id: int, expense_group_ids: List[str]):
    """
    Schedule Credit Card Charge creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :return: None
    """
    if expense_group_ids:
        expense_groups = ExpenseGroup.objects.filter(
            Q(tasklog__id__isnull=True) | ~Q(tasklog__status__in=['IN_PROGRESS', 'COMPLETE']),
            workspace_id=workspace_id, id__in=expense_group_ids,
            creditcardcharge__id__isnull=True, exported_at__isnull=True
        ).all()

        chain = Chain(cached=False)

        fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
        chain.append('apps.fyle.helpers.sync_dimensions', fyle_credentials, workspace_id)

        for expense_group in expense_groups:
            expense_amount = expense_group.expenses.first().amount
            export_type = 'CREATING_CREDIT_CARD_CHARGE'
            if expense_amount < 0:
                export_type = 'CREATING_CREDIT_CARD_REFUND'

            task_log, _ = TaskLog.objects.get_or_create(
                workspace_id=expense_group.workspace_id,
                expense_group=expense_group,
                defaults={
                    'status': 'ENQUEUED',
                    'type': export_type
                }
            )

            if task_log.status not in ['IN_PROGRESS', 'ENQUEUED']:
                task_log.type = export_type
                task_log.status = 'ENQUEUED'
                task_log.save()

            chain.append('apps.netsuite.tasks.create_credit_card_charge', expense_group, task_log.id)

            task_log.save()
        if chain.length() > 1:
            chain.run()


def schedule_expense_reports_creation(workspace_id: int, expense_group_ids: List[str]):
    """
    Schedule expense reports creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :return: None
    """
    if expense_group_ids:
        expense_groups = ExpenseGroup.objects.filter(
            Q(tasklog__id__isnull=True) | ~Q(tasklog__status__in=['IN_PROGRESS', 'COMPLETE']),
            workspace_id=workspace_id, id__in=expense_group_ids,
            expensereport__id__isnull=True, exported_at__isnull=True
        ).all()

        chain = Chain(cached=False)

        fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
        chain.append('apps.fyle.helpers.sync_dimensions', fyle_credentials, workspace_id)

        for expense_group in expense_groups:
            task_log, _ = TaskLog.objects.get_or_create(
                workspace_id=expense_group.workspace_id,
                expense_group=expense_group,
                defaults={
                    'status': 'ENQUEUED',
                    'type': 'CREATING_EXPENSE_REPORT'
                }
            )

            if task_log.status not in ['IN_PROGRESS', 'ENQUEUED']:
                task_log.type = 'CREATING_EXPENSE_REPORT'
                task_log.status = 'ENQUEUED'
                task_log.save()

            chain.append('apps.netsuite.tasks.create_expense_report', expense_group, task_log.id)
            task_log.save()
        if chain.length() > 1:
            chain.run()


def schedule_journal_entry_creation(workspace_id: int, expense_group_ids: List[str]):
    """
    Schedule journal entries creation
    :param expense_group_ids: List of expense group ids
    :param workspace_id: workspace id
    :return: None
    """
    if expense_group_ids:
        expense_groups = ExpenseGroup.objects.filter(
            Q(tasklog__id__isnull=True) | ~Q(tasklog__status__in=['IN_PROGRESS', 'COMPLETE']),
            workspace_id=workspace_id, id__in=expense_group_ids, journalentry__id__isnull=True, exported_at__isnull=True
        ).all()

        chain = Chain(cached=False)

        fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
        chain.append('apps.fyle.helpers.sync_dimensions', fyle_credentials, workspace_id)

        for expense_group in expense_groups:
            task_log, _ = TaskLog.objects.get_or_create(
                workspace_id=expense_group.workspace_id,
                expense_group=expense_group,
                defaults={
                    'status': 'ENQUEUED',
                    'type': 'CREATING_JOURNAL_ENTRY'
                }
            )

            if task_log.status not in ['IN_PROGRESS', 'ENQUEUED']:
                task_log.type = 'CREATING_JOURNAL_ENTRY'
                task_log.status = 'ENQUEUED'
                task_log.save()

            chain.append('apps.netsuite.tasks.create_journal_entry', expense_group, task_log.id)
            task_log.save()
        if chain.length() > 1:
            chain.run()


def check_expenses_reimbursement_status(expenses):
    all_expenses_paid = True

    for expense in expenses:
        reimbursement = Reimbursement.objects.filter(settlement_id=expense.settlement_id).first()

        if (reimbursement and reimbursement.state != 'COMPLETE') or not reimbursement:
            all_expenses_paid = False

    return all_expenses_paid


def create_netsuite_payment_objects(netsuite_objects, object_type, workspace_id):
    netsuite_payment_objects = {}

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

    try:
        netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id)
    except NetSuiteRateLimitError:
        logger.info('Rate limit error, workspace_id - %s', workspace_id)
        return
    except NetSuiteLoginError:
        logger.info('Invalid credentials, workspace_id - %s', workspace_id)
        return

    for netsuite_object in netsuite_objects:
        entity_id = netsuite_object.entity_id

        expense_group_reimbursement_status = check_expenses_reimbursement_status(
            netsuite_object.expense_group.expenses.all())

        netsuite_object_task_log = TaskLog.objects.get(
            expense_group=netsuite_object.expense_group, status='COMPLETE')

        # When the record is deleted, netsuite sdk would throw an exception RCRD_DSNT_EXIST
        try:
            if object_type == 'BILL':
                netsuite_entry = netsuite_connection.get_bill(netsuite_object_task_log.detail['internalId'])
            else:
                netsuite_entry = netsuite_connection.get_expense_report(netsuite_object_task_log.detail['internalId'])
        except Exception:
            netsuite_entry = None

        if netsuite_entry and netsuite_entry['status'] != netsuite_paid_state and expense_group_reimbursement_status:
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

    return netsuite_payment_objects


def process_vendor_payment(entity_object, workspace_id, object_type):
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

            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
            netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id)

            first_object_id = vendor_payment_lineitems[0].doc_id
            if object_type == 'BILL':
                first_object = netsuite_connection.get_bill(first_object_id)
            else:
                first_object = netsuite_connection.get_expense_report(first_object_id)
            created_vendor_payment = netsuite_connection.post_vendor_payment(
                vendor_payment_object, vendor_payment_lineitems, first_object
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
                paid_object.save()

            task_log.detail = created_vendor_payment
            task_log.vendor_payment = vendor_payment_object
            task_log.status = 'COMPLETE'

            task_log.save()
    except NetSuiteCredentials.DoesNotExist:
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
        task_log.detail = all_details

        task_log.save()

    except NetSuiteRateLimitError:
        logger.info('Rate limit error, workspace_id - %s', workspace_id)
        task_log.status = 'FAILED'
        task_log.detail = {
            'error': 'Rate limit error'
        }

        task_log.save()

    except BulkError as exception:
        logger.info(exception.response)
        detail = exception.response
        task_log.status = 'FAILED'
        task_log.detail = detail

        task_log.save()


def create_vendor_payment(workspace_id):
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)

    try:
        platform = PlatformConnector(fyle_credentials=fyle_credentials)
    except InvalidTokenError:
        logger.info('Invalid Fyle refresh token for workspace %s', workspace_id)
        return
    platform.reimbursements.sync()

    bills = Bill.objects.filter(
        payment_synced=False, expense_group__workspace_id=workspace_id,
        expense_group__fund_source='PERSONAL', expense_group__exported_at__isnull=False
    ).all()

    expense_reports = ExpenseReport.objects.filter(
        payment_synced=False, expense_group__workspace_id=workspace_id,
        expense_group__fund_source='PERSONAL', expense_group__exported_at__isnull=False
    ).all()

    if bills:
        bill_entity_map = create_netsuite_payment_objects(bills, 'BILL', workspace_id)

        for entity_object_key in bill_entity_map:
            entity_id = entity_object_key
            entity_object = bill_entity_map[entity_id]

            process_vendor_payment(entity_object, workspace_id, 'BILL')

    if expense_reports:
        expense_report_entity_map = create_netsuite_payment_objects(
            expense_reports, 'EXPENSE REPORT', workspace_id)

        for entity_object_key in expense_report_entity_map:
            entity_id = entity_object_key
            entity_object = expense_report_entity_map[entity_id]

            process_vendor_payment(entity_object, workspace_id, 'EXPENSE REPORT')


def schedule_vendor_payment_creation(sync_fyle_to_netsuite_payments, workspace_id):
    general_mappings: GeneralMapping = GeneralMapping.objects.filter(workspace_id=workspace_id).first()
    if general_mappings and sync_fyle_to_netsuite_payments and general_mappings.vendor_payment_account_id:
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

    try:
        netsuite_connection = NetSuiteConnector(netsuite_credentials, workspace_id)
    except NetSuiteRateLimitError:
        logger.info('Rate limit error, workspace_id - %s', workspace_id)
        return
    except NetSuiteLoginError:
        logger.error('NetSuite login error, workspace_id - %s', workspace_id)
        return

    bills = Bill.objects.filter(
        expense_group__workspace_id=workspace_id, paid_on_netsuite=False, expense_group__fund_source='PERSONAL'
    ).all()

    expense_reports = ExpenseReport.objects.filter(
        expense_group__workspace_id=workspace_id, paid_on_netsuite=False, expense_group__fund_source='PERSONAL'
    ).all()

    if bills:
        internal_ids = get_all_internal_ids(bills)
        for bill in bills:
            try:
                bill_object = netsuite_connection.get_bill(internal_ids[bill.expense_group.id]['internal_id'])
                if bill_object['status'] == netsuite_paid_state:
                    line_items = BillLineitem.objects.filter(bill_id=bill.id)
                    for line_item in line_items:
                        expense = line_item.expense
                        expense.paid_on_netsuite = True
                        expense.save()

                    bill.paid_on_netsuite = True
                    bill.payment_synced = True
                    bill.save()
            except NetSuiteRequestError as exception:
                logger.info({'error': exception})
                pass

    if expense_reports:
        internal_ids = get_all_internal_ids(expense_reports)

        for expense_report in expense_reports:
            try:
                expense_report_object = netsuite_connection.get_expense_report(
                    internal_ids[expense_report.expense_group.id]['internal_id'])
                if expense_report_object['status'] == netsuite_paid_state:
                    line_items = ExpenseReportLineItem.objects.filter(expense_report_id=expense_report.id)
                    for line_item in line_items:
                        expense = line_item.expense
                        expense.paid_on_netsuite = True
                        expense.save()

                    expense_report.paid_on_netsuite = True
                    expense_report.payment_synced = True
                    expense_report.save()
            except NetSuiteRequestError as exception:
                logger.info({'error': exception})
                pass


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


def get_valid_reimbursement_ids(reimbursement_ids: List, platform: PlatformConnector) -> List[str]:
    chunk_size = 10
    count_of_reimbursements = len(reimbursement_ids)

    valid_reimbursement_ids = []
    for index in range(0, count_of_reimbursements, chunk_size):
        partitioned_list = reimbursement_ids[index:index + chunk_size]

        id_filter = 'in.{}'.format(tuple(partitioned_list)).replace('\'', '"') \
            if len(partitioned_list) > 1 else 'eq.{}'.format(partitioned_list[0])

        query_params = {
            'id': id_filter,
            'is_paid': 'eq.false'
        }

        reimbursements = platform.reimbursements.search_reimbursements(query_params)

        for reimbursements_generator in reimbursements:
            valid_ids = [reimbursement['id'] for reimbursement in reimbursements_generator['data']]
            valid_reimbursement_ids.extend(valid_ids)

    return valid_reimbursement_ids


def process_reimbursements(workspace_id):
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)

    try:
        platform = PlatformConnector(fyle_credentials=fyle_credentials)
    except InvalidTokenError:
        logger.info('Invalid Fyle refresh token for workspace %s', workspace_id)
        return

    platform.reimbursements.sync()

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
        # Validating deleted reimbursements
        valid_reimbursement_ids = get_valid_reimbursement_ids(reimbursement_ids, platform)

        chunk_size = 20

        for index in range(0, len(valid_reimbursement_ids), chunk_size):
            partitioned_list = valid_reimbursement_ids[index:index + chunk_size]

            if partitioned_list:
                reimbursements_list = []
                for reimbursement_id in partitioned_list:
                    reimbursement_object = {'id': reimbursement_id}
                    reimbursements_list.append(reimbursement_object)

                try:
                    platform.reimbursements.bulk_post_reimbursements(reimbursements_list)
                    platform.reimbursements.sync()
                except Exception as error:
                    error = traceback.format_exc()
                    error = {
                        'error': error
                    }
                    logger.exception(error)


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
