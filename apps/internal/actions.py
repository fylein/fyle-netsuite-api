from typing import Dict

from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import Workspace, NetSuiteCredentials


def get_accounting_fields(query_params: Dict):
    org_id = query_params.get('org_id')
    resource_type = query_params.get('resource_type')

    workspace = Workspace.objects.get(fyle_org_id=org_id)
    workspace_id = workspace.id
    ns_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace.id)

    ns_connection = NetSuiteConnector(netsuite_credentials=ns_credentials, workspace_id=workspace_id)

    return ns_connection.get_accounting_fields(resource_type)
