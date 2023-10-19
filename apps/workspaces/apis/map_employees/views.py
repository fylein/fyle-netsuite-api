from rest_framework import generics
from apps.workspaces.apis.map_employees.serializers import MapEmployeesSerializer
from apps.workspaces.models import Workspace


class MapEmployeesView(generics.RetrieveUpdateAPIView):

    serializer_class = MapEmployeesSerializer

    def get_object(self):
        return Workspace.objects.filter(id=self.kwargs['workspace_id']).first()   
