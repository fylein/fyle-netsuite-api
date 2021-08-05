from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from .helpers import validate_and_trigger_auto_map_employees
from .serializers import GeneralMappingSerializer, SubsidiaryMappingSerializer
from .models import GeneralMapping, SubsidiaryMapping


class SubsidiaryMappingView(generics.ListCreateAPIView):
    """
    Subsidiary mappings view
    """
    serializer_class = SubsidiaryMappingSerializer

    def get(self, request, *args, **kwargs):
        """
        Get subsidiary mapping
        """
        try:
            subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=kwargs['workspace_id'])

            return Response(
                data=self.serializer_class(subsidiary_mapping).data,
                status=status.HTTP_200_OK
            )
        except SubsidiaryMapping.DoesNotExist:
            return Response(
                {
                    'message': 'Subsidiary mappings do not exist for the workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class GeneralMappingView(generics.ListCreateAPIView):
    """
    General mappings view
    """
    serializer_class = GeneralMappingSerializer

    def get(self, request, *args, **kwargs):
        """
        Get general mappings
        """
        try:
            general_mapping = GeneralMapping.objects.get(workspace_id=kwargs['workspace_id'])

            return Response(
                data=self.serializer_class(general_mapping).data,
                status=status.HTTP_200_OK
            )
        except GeneralMapping.DoesNotExist:
            return Response(
                {
                    'message': 'General mappings do not exist for the workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class AutoMapEmployeeView(generics.CreateAPIView):
    """
    Auto Map Employees view
    """

    def post(self, request, *args, **kwargs):
        """
        Trigger Auto Map employees
        """
        validate_and_trigger_auto_map_employees(kwargs['workspace_id'])

        return Response(
            status=status.HTTP_200_OK
        )
