from rest_framework import generics

from apps.workspaces.models import Workspace
from apps.workspaces.apis.advanced_settings.serializers import AdvancedSettingsSerializer


class AdvancedSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = AdvancedSettingsSerializer

    def get_object(self):
        return Workspace.objects.filter(id=self.kwargs['workspace_id']).first()
