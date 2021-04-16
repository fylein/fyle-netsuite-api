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
        users = cache.get(str(workspace_id))
        if users:
            print('cache foundddddd', users)
            if request.user.id in users:
                print('allowed user')
                return True
            print('forbidden because user not found in cache')
            return False
        else:
            users = Workspace.objects.filter(pk=workspace_id).values_list('user', flat=True)
            print('cache not exist for this workspace')
            if user.id in users:
                print('cache set successfully')
                cache.set(str(workspace_id), users)
                return True

            print('forbidden because user not found in workspace user mapping')
            return False