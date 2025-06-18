from django.db.models import Q
from apps.workspaces.models import NetSuiteCredentials, Workspace
from apps.netsuite.connector import NetSuiteConnector

folder_created_workspace_ids = []

prod_workspaces = Workspace.objects.exclude(
    name__iregex=r'(fyle|test)',
    id__in=folder_created_workspace_ids
)

for workspace in prod_workspaces:
    try:
        netsuite_credential = NetSuiteCredentials.get_active_netsuite_credentials(workspace.id)
        netsuite_connection = NetSuiteConnector(netsuite_credential, workspace.id)
        netsuite_connection.connection.folders.post({
            'externalId': workspace.fyle_org_id,
            'name': 'Fyle Attachments - {0}'.format(workspace.name)
        })
        folder_created_workspace_ids.append(workspace.id)
        print('Done for workspace {} with id {}'.format(workspace.name, workspace.id))
        print('Current folder_created_workspace_ids: {}'.format(folder_created_workspace_ids))
    except Exception:
        print('Error while creating folder in NetSuite for workspace_id {}'.format(workspace.id))
