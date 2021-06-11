from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import permissions

from apps.workspaces.models import Workspace

User = get_user_model()


class WorkspacePermissions(permissions.BasePermission):
    """
    Permission check for users <> workspaces
    """
    @staticmethod
    def validate_and_cache(workspace_users, user: User, workspace_id: str, cache_users: bool = False):
        if user.id in workspace_users:
            if cache_users:
                # Setting cache to expire after 2 days
                cache.set(workspace_id, workspace_users, 172800)
            return True

        return False

    def has_permission(self, request, view):
        workspace_id = str(view.kwargs.get('workspace_id'))
        user = request.user
        workspace_users = cache.get(workspace_id)

        if workspace_users:
            print('asdasd',self.validate_and_cache(workspace_users, user, workspace_id))
            # TODO: check this buggar later
            return True
        else:
            workspace_users = Workspace.objects.filter(pk=workspace_id).values_list('user', flat=True)
            print('2222',self.validate_and_cache(workspace_users, user, workspace_id, True))
            return self.validate_and_cache(workspace_users, user, workspace_id, True)
