from apps.workspaces.tasks import post_to_integration_settings
from apps.workspaces.models import Workspace

workspaces = Workspace.objects.filter(onboarding_state='COMPLETE')

for workspace in workspaces:
    try:
        print("Posting to integration settings for workspace: {}".format(workspace.id))
        post_to_integration_settings(workspace.id, True)
    except Exception as e:
        print("Error while posting to integration settings for workspace: {}".format(workspace.id))
        print(e)
