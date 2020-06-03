from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from fyle_netsuite_api.utils import assert_valid

from .serializers import EmployeeMappingSerializer, \
    CategoryMappingSerializer, CostCenterMappingSerializer, ProjectMappingSerializer
from .models import EmployeeMapping, CategoryMapping, CostCenterMapping, ProjectMapping
from .utils import MappingUtils


class EmployeeMappingView(generics.ListCreateAPIView):
    """
    Employee mappings view
    """
    serializer_class = EmployeeMappingSerializer

    def get_queryset(self):
        return EmployeeMapping.objects.filter(workspace_id=self.kwargs['workspace_id']).order_by('-updated_at').all()

    def post(self, request, *args, **kwargs):
        """
        Post employee mapping view
        """
        employee_mapping_payload = request.data

        assert_valid(employee_mapping_payload is not None, 'Request body is empty')

        mapping_utils = MappingUtils(kwargs['workspace_id'])
        employee_mapping_object = mapping_utils.create_or_update_employee_mapping(employee_mapping_payload)

        return Response(
            data=self.serializer_class(employee_mapping_object).data,
            status=status.HTTP_200_OK
        )


class CategoryMappingView(generics.ListCreateAPIView):
    """
    Category mappings view
    """
    serializer_class = CategoryMappingSerializer

    def get_queryset(self):
        return CategoryMapping.objects.filter(workspace_id=self.kwargs['workspace_id']).order_by('-updated_at').all()

    def post(self, request, *args, **kwargs):
        """
        Post category mapping view
        """
        category_mapping_payload = request.data

        assert_valid(category_mapping_payload is not None, 'Request body is empty')

        mapping_utils = MappingUtils(kwargs['workspace_id'])
        category_mapping_object = mapping_utils.create_or_update_category_mapping(category_mapping_payload)

        return Response(
            data=self.serializer_class(category_mapping_object).data,
            status=status.HTTP_200_OK
        )


class CostCenterMappingView(generics.ListCreateAPIView):
    """
    Cost center mappings view
    """
    serializer_class = CostCenterMappingSerializer

    def get_queryset(self):
        return CostCenterMapping.objects.filter(workspace_id=self.kwargs['workspace_id']).order_by('-updated_at').all()

    def post(self, request, *args, **kwargs):
        """
        Post cost center mapping view
        """
        cost_center_mapping_payload = request.data

        assert_valid(cost_center_mapping_payload is not None, 'Request body is empty')

        mapping_utils = MappingUtils(kwargs['workspace_id'])
        cost_center_mapping_object = mapping_utils.create_or_update_cost_center_mapping(cost_center_mapping_payload)

        return Response(
            data=self.serializer_class(cost_center_mapping_object).data,
            status=status.HTTP_200_OK
        )


class ProjectMappingView(generics.ListCreateAPIView):
    """
    Project mappings view
    """
    serializer_class = ProjectMappingSerializer

    def get_queryset(self):
        return ProjectMapping.objects.filter(workspace_id=self.kwargs['workspace_id']).order_by('-updated_at').all()

    def post(self, request, *args, **kwargs):
        """
        Post project mapping view
        """
        project_mapping_payload = request.data

        assert_valid(project_mapping_payload is not None, 'Request body is empty')

        mapping_utils = MappingUtils(kwargs['workspace_id'])
        project_mapping_object = mapping_utils.create_or_update_project_mapping(project_mapping_payload)

        return Response(
            data=self.serializer_class(project_mapping_object).data,
            status=status.HTTP_200_OK
        )
