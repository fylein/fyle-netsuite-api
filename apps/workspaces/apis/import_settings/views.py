from rest_framework import generics

from apps.workspaces.apis.import_settings.serializers import ImportSettingsSerializer
from apps.workspaces.models import Workspace


class ImportSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = ImportSettingsSerializer

    def get_object(self):
        return Workspace.objects.filter(id=self.kwargs['workspace_id']).first()
