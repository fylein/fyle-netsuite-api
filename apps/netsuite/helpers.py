from datetime import datetime, timezone
import logging

from django_q.models import OrmQ

from django.utils.module_loading import import_string

from apps.mappings.constants import SYNC_METHODS
from apps.workspaces.models import Configuration, Workspace, NetSuiteCredentials
from apps.mappings.queue import construct_tasks_and_chain_import_fields_to_fyle
from apps.netsuite.connector import NetSuiteConnector

from .tasks import schedule_vendor_payment_creation, schedule_netsuite_objects_status_sync, \
    schedule_reimbursements_sync

logger = logging.getLogger(__name__)


def sync_override_tax_items(netsuite_credentials: NetSuiteCredentials, workspace_id: int):
    try:
        netsuite_connection = NetSuiteConnector(
            netsuite_credentials=netsuite_credentials,
            workspace_id=workspace_id,
            search_body_fields_only=False
        )
        netsuite_connection.sync_tax_items()
    except Exception as e:
        logger.info("Error during sync of tax items with search body fields: workspace_id: %s", workspace_id)
        logger.info(e)
    

def schedule_payment_sync(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Intance
    :return: None
    """
    schedule_vendor_payment_creation(
        sync_fyle_to_netsuite_payments=configuration.sync_fyle_to_netsuite_payments,
        workspace_id=configuration.workspace_id
    )

    schedule_netsuite_objects_status_sync(
        sync_netsuite_to_fyle_payments=configuration.sync_netsuite_to_fyle_payments,
        workspace_id=configuration.workspace_id
    )

    schedule_reimbursements_sync(
        sync_netsuite_to_fyle_payments=configuration.sync_netsuite_to_fyle_payments,
        workspace_id=configuration.workspace_id
    )

def check_interval_and_sync_dimension(workspace_id):
    """
    Check sync interval and sync dimension
    :param workspace_id: Workspace ID
    """
    workspace = Workspace.objects.get(pk=workspace_id)
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace.id)

    if workspace.destination_synced_at:
        time_interval = datetime.now(timezone.utc) - workspace.source_synced_at

    if workspace.destination_synced_at is None or time_interval.days > 0:
        sync_dimensions(netsuite_credentials, workspace.id)
        workspace.destination_synced_at = datetime.now()
        workspace.save(update_fields=['destination_synced_at'])

def sync_dimensions(ns_credentials: NetSuiteCredentials, workspace_id: int, dimensions: list = []) -> None:
    netsuite_connection = import_string('apps.netsuite.connector.NetSuiteConnector')(ns_credentials, workspace_id)
    if not dimensions:
        dimensions = [
            'expense_categories', 'locations', 'vendors', 'currencies', 'classifications',
            'departments', 'employees', 'accounts', 'custom_segments', 'projects', 'customers', 'tax_items', 'items'
        ]

    for dimension in dimensions:
        try:
            sync = getattr(netsuite_connection, 'sync_{}'.format(dimension))
            sync()
        except Exception as exception:
            logger.info(exception)


def get_import_categories_settings(configurations: Configuration):
    """
    Get import categories settings
    :return: is_3d_mapping_enabled, destination_field, destination_sync_methods
    """
    destination_sync_methods = []
    destination_field = None
    is_3d_mapping_enabled = False

    if configurations.import_items:
        destination_sync_methods.append(SYNC_METHODS['ITEM'])

    if (configurations.reimbursable_expenses_object and configurations.reimbursable_expenses_object == 'EXPENSE REPORT') or configurations.corporate_credit_card_expenses_object == 'EXPENSE REPORT':
        destination_sync_methods.append(SYNC_METHODS['EXPENSE_CATEGORY'])
        destination_field = 'EXPENSE_CATEGORY'

    if configurations.reimbursable_expenses_object != 'EXPENSE REPORT' and (
        configurations.reimbursable_expenses_object in ('BILL', 'JOURNAL ENTRY')
        or configurations.corporate_credit_card_expenses_object in ('BILL', 'JOURNAL ENTRY', 'CREDIT CARD CHARGE')):
        destination_sync_methods.append(SYNC_METHODS['ACCOUNT'])
        destination_field = 'ACCOUNT'

    if configurations.reimbursable_expenses_object == 'EXPENSE REPORT' and \
    configurations.corporate_credit_card_expenses_object in ('BILL', 'CREDIT CARD CHARGE', 'JOURNAL ENTRY'):
        is_3d_mapping_enabled = True

    return is_3d_mapping_enabled, destination_field, destination_sync_methods


def handle_refresh_dimensions(workspace_id, dimensions_to_sync):

    workspace = Workspace.objects.get(pk=workspace_id)
    netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace.id)

    configurations = Configuration.objects.filter(workspace_id=workspace.id).first()
    workspace_id = workspace.id

    if configurations:
        construct_tasks_and_chain_import_fields_to_fyle(workspace_id)

    sync_dimensions(netsuite_credentials, workspace.id, dimensions_to_sync)

    # Update destination_synced_at to current time only when full refresh happens
    if not dimensions_to_sync:
        workspace.destination_synced_at = datetime.now()
        workspace.save(update_fields=['destination_synced_at'])


def check_if_task_exists_in_ormq(func: str, payload: str) -> bool:
    """
    Check if task exists in ORMQ
    :param func: Function name
    :param payload: Payload
    :return: True if task exists in ORMQ else False
    """
    ormqs = OrmQ.objects.all()

    for ormq in ormqs:
        if ormq.task['func'] == func and str(ormq.task['args'][0]) == str(payload):
            return True

    return False
