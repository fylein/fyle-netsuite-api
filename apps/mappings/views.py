from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from fyle_netsuite_api.utils import assert_valid

from .serializers import GeneralMappingSerializer, SubsidiaryMappingSerializer
from .models import GeneralMapping, SubsidiaryMapping
from .utils import MappingUtils


class SubsidiaryMappingView(generics.ListCreateAPIView):
    """
    Subsidiary mappings view
    """
    serializer_class = SubsidiaryMappingSerializer
    queryset = SubsidiaryMapping.objects.all()

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
            subsidiary_mapping = self.queryset.get(workspace_id=kwargs['workspace_id'])
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
    queryset = GeneralMapping.objects.all()

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
            general_mapping = self.queryset.get(workspace_id=kwargs['workspace_id'])
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
