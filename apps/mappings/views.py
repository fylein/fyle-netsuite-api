from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from django_q.tasks import Chain

from fyle_netsuite_api.utils import assert_valid
from apps.workspaces.models import WorkspaceGeneralSettings

from .serializers import GeneralMappingSerializer, SubsidiaryMappingSerializer
from .models import GeneralMapping, SubsidiaryMapping
from .utils import MappingUtils


class SubsidiaryMappingView(generics.ListCreateAPIView):
    """
    Subsidiary mappings view
    """
    serializer_class = SubsidiaryMappingSerializer

    def post(self, request, *args, **kwargs):
        """
        Post Subsidiary mapping view
        """
        subsidiary_mapping_payload = request.data

        assert_valid(subsidiary_mapping_payload is not None, 'Request body is empty')

        mapping_utils = MappingUtils(kwargs['workspace_id'])
        subsidiary_mapping_object = mapping_utils.create_or_update_subsidiary_mapping(subsidiary_mapping_payload)

        return Response(
            data=self.serializer_class(subsidiary_mapping_object).data,
            status=status.HTTP_200_OK
        )

    def get(self, request, *args, **kwargs):
        """
        Get subsidiary mappings
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

    def post(self, request, *args, **kwargs):
        """
        Post General mapping view
        """
        general_mapping_payload = request.data

        assert_valid(general_mapping_payload is not None, 'Request body is empty')

        mapping_utils = MappingUtils(kwargs['workspace_id'])
        general_mapping_object = mapping_utils.create_or_update_general_mapping(general_mapping_payload)

        return Response(
            data=self.serializer_class(general_mapping_object).data,
            status=status.HTTP_200_OK
        )

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
        try:
            workspace_id = kwargs['workspace_id']
            general_settings = WorkspaceGeneralSettings.objects.get(workspace_id=workspace_id)

            chain = Chain(cached=True)

            if not general_settings.auto_map_employees:
                return Response(
                    data={
                        'message': 'Employee mapping preference not found for this workspace'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            chain.append('apps.mappings.tasks.async_auto_map_employees', workspace_id)

            general_mappings = GeneralMapping.objects.get(workspace_id=workspace_id)
            if general_mappings.default_ccc_account_name:
                chain.append('apps.mappings.tasks.async_auto_map_ccc_account', workspace_id)

            chain.run()

            return Response(
                data={},
                status=status.HTTP_200_OK
            )

        except GeneralMapping.DoesNotExist:
            return Response(
                {
                    'message': 'General mappings do not exist for this workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
