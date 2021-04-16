from time import time
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import permissions

from apps.workspaces.models import Workspace

User = get_user_model()


class WorkspacePermissions(permissions.BasePermission):
    """
    Permission check for users <> workspaces
    """

    def validate_and_cache(self, workspace_users, user: User, workspace_id: str, cache_users: bool = False):
        if user.id in workspace_users:
            if cache_users:
                cache.set(workspace_id, workspace_users)
            print('allowed user', 'cache set successfully' if cache_users else '')
            return True

        print('forbidden because user not found in ', 'workspace user mapping' if cache_users else 'cache')
        return False

    def has_permission(self, request, view):
        start = time()
        workspace_id = str(view.kwargs.get('workspace_id'))
        user = request.user
        workspace_users = cache.get(workspace_id)
        if workspace_users:
            print('cache found', workspace_users)
            valid_request = self.validate_and_cache(workspace_users, user, workspace_id)
            end = time()
            print('New implementation with cached workspace took ', end - start, ' to complete')
            return valid_request
        else:
            workspace_users = Workspace.objects.filter(pk=workspace_id).values_list('user', flat=True)
            valid_request = self.validate_and_cache(workspace_users, user, workspace_id, True)
            end = time()
            print('New implementation without cached workspace took ', end - start, ' to complete')
            return valid_request
