from datetime import datetime, timezone
import logging
import json

from django.utils.module_loading import import_string

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
            'departments', 'employees', 'accounts', 'custom_segments', 'projects', 'customers', 'tax_items', 'items'
        ]

    for dimension in dimensions:
        try:
            sync = getattr(netsuite_connection, 'sync_{}'.format(dimension))
            sync()
        except Exception as exception:
            logger.info(exception)


def parse_error_and_get_message(raw_response):
    try:
        if raw_response == '<HTML><HEAD>' or raw_response == '<html>':
            return 'HTML bad response from NetSuite'
        raw_response = raw_response.replace("'", '"')\
            .replace("False", 'false')\
            .replace("True", 'true')\
            .replace("None", 'null')
        parsed_response = json.loads(raw_response)
        return get_message_from_parsed_error(parsed_response)
    except Exception:
        raw_response = raw_response.replace('"creditCardCharge"', 'creditCardCharge')\
            .replace('""{', '{').replace('}""', '}')\
            .replace('"{', '{').replace('}"', '}')\
            .replace('\\"', '"').replace('\\', '')\
            .replace('"https://', "'https://").replace('.html"', ".html'")\
            .replace('="', "=").replace('">', ">")
        parsed_response = json.loads(raw_response)
        return get_message_from_parsed_error(parsed_response)


def get_message_from_parsed_error(parsed_response):
    try:
        if 'error' in parsed_response:
            if 'message' in parsed_response['error']:
                if 'message' in parsed_response['error']['message']:
                    return parsed_response['error']['message']['message']
                return parsed_response['error']['message']
        elif 'message' in parsed_response:
            if 'message' in parsed_response['message']:
                return parsed_response['message']['message']
    except Exception:
        raise
