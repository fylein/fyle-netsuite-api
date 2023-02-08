from django.db.models import Q
from apps.workspaces.models import NetSuiteCredentials, Workspace
from apps.netsuite.connector import NetSuiteConnector


prod_workspaces = Workspace.objects.exclude(
    name__iregex=r'(fyle|test)'
)

for workspace in prod_workspaces:
    try:
        netsuite_credential = NetSuiteCredentials.objects.get(workspace_id=workspace.id)
        netsuite_connection = NetSuiteConnector(netsuite_credential, workspace.id)
        netsuite_connection.connection.folders.post({
            'externalId': workspace.fyle_org_id,
            'name': 'Fyle Attachments - {0}'.format(workspace.name)
        })
        print('Done for workspace {} with id {}'.format(workspace.name, workspace.id))
    except Exception:
        print('Error while creating folder in NetSuite for workspace_id {}'.format(workspace.id))
