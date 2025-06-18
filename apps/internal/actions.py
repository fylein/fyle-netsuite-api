from typing import Dict

from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import Workspace, NetSuiteCredentials


def get_netsuite_connection(query_params: Dict):
    org_id = query_params.get('org_id')

    workspace = Workspace.objects.get(fyle_org_id=org_id)
    workspace_id = workspace.id
    try:
        ns_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id)
        return NetSuiteConnector(netsuite_credentials=ns_credentials, workspace_id=workspace_id)
    except NetSuiteCredentials.DoesNotExist:
        raise Exception('Netsuite credentials not found')


def get_accounting_fields(query_params: Dict):
    ns_connection = get_netsuite_connection(query_params)
    resource_type = query_params.get('resource_type')
    internal_id = query_params.get('internal_id')

    return ns_connection.get_accounting_fields(resource_type, internal_id)


def get_exported_entry(query_params: Dict):
    ns_connection = get_netsuite_connection(query_params)
    resource_type = query_params.get('resource_type')
    internal_id = query_params.get('internal_id')

    return ns_connection.get_exported_entry(resource_type, internal_id)
