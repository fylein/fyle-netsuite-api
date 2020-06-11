from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from fyle_netsuite_api.utils import assert_valid

from .serializers import SubsidiaryMappingSerializer
from .models import SubsidiaryMapping
from .utils import MappingUtils


class SubsidiaryMappingView(generics.ListCreateAPIView):
    """
    Subsidiary mappings view
    """
    serializer_class = SubsidiaryMappingSerializer

    def get_queryset(self):
        return SubsidiaryMapping.objects.filter(workspace_id=self.kwargs['workspace_id']).order_by('-updated_at').all()

    def post(self, request, *args, **kwargs):
        """
        Post Subsidiary mapping view
        """
        project_mapping_payload = request.data

        assert_valid(project_mapping_payload is not None, 'Request body is empty')

        mapping_utils = MappingUtils(kwargs['workspace_id'])
        subsidiary_mapping_object = mapping_utils.create_or_update_subsidiary_mapping(project_mapping_payload)

        return Response(
            data=self.serializer_class(subsidiary_mapping_object).data,
            status=status.HTTP_200_OK
        )
