from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import permissions

from apps.workspaces.models import Workspace

User = get_user_model()


class WorkspacePermissions(permissions.BasePermission):
    """
    Permission check for users <> workspaces
    """

    def has_permission(self, request, view):
        workspace_id = view.kwargs.get('workspace_id')
        user = request.user
        workspace_users = cache.get(str(workspace_id))
        if workspace_users:
            print('cache foundddddd', workspace_users)
            if user.id in workspace_users:
                print('allowed user')
                return True
            print('forbidden because user not found in cache')
            return False
        else:
            workspace_users = Workspace.objects.filter(pk=workspace_id).values_list('user', flat=True)
            print('cache not exist for this workspace')
            if user.id in workspace_users:
                print('cache set successfully')
                cache.set(str(workspace_id), workspace_users)
                return True

            print('forbidden because user not found in workspace user mapping')
            return False
