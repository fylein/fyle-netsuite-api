from datetime import datetime, timezone
import logging

from django.utils.module_loading import import_string

from rest_framework.exceptions import AuthenticationFailed

from apps.workspaces.models import Configuration, Workspace, NetSuiteCredentials

from .tasks import schedule_vendor_payment_creation, schedule_netsuite_objects_status_sync, \
    schedule_reimbursements_sync

logger = logging.getLogger(__name__)


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

def check_interval_and_sync_dimension(workspace: Workspace, netsuite_credentials: NetSuiteCredentials) -> bool:
    """
    Check sync interval and sync dimension
    :param workspace: Workspace Instance
    :param netsuite_credentials: NetSuiteCredentials Instance

    return: True/False based on sync
    """
    if workspace.destination_synced_at:
        time_interval = datetime.now(timezone.utc) - workspace.source_synced_at

    if workspace.destination_synced_at is None or time_interval.days > 0:
        sync_dimensions(netsuite_credentials, workspace.id)
        return True

    return False

def sync_dimensions(ns_credentials: NetSuiteCredentials, workspace_id: int, dimensions: list = []) -> None:
    netsuite_connection = import_string('apps.netsuite.connector.NetSuiteConnector')(ns_credentials, workspace_id)
    if not dimensions:
        dimensions = [
            'expense_categories', 'locations', 'vendors', 'currencies', 'classifications',
            'departments', 'employees', 'accounts', 'custom_segments', 'projects', 'customers', 'tax_items'
        ]

    for dimension in dimensions:
        try:
            sync = getattr(netsuite_connection, 'sync_{}'.format(dimension))
            sync()
        except Exception as exception:
            logger.info(exception)
