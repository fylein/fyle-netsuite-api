from django.contrib.auth import get_user_model
from rest_framework import permissions

from apps.workspaces.models import Workspace

User = get_user_model()


class WorkspacePermissions(permissions.BasePermission):
    """
    Permission check for users <> workspaces
    """

    def has_permission(self, request, view):
        workspace_id = view.kwargs.get('workspace_id')
        user_id = request.user
        user = User.objects.get(user_id=user_id)
        workspaces = Workspace.objects.filter(user__in=[user], pk=workspace_id).all()
        if not workspaces:
            return False
        return True
