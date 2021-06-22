from typing import List, Dict

from rest_framework.generics import ListCreateAPIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from django_q.tasks import Chain
from django_q.models import Schedule

from fyle_accounting_mappings.models import MappingSetting
from fyle_accounting_mappings.views import logger
from fyle_accounting_mappings.exceptions import BulkError
from fyle_accounting_mappings.serializers import MappingSettingSerializer

from fyle_netsuite_api.utils import assert_valid
from apps.workspaces.models import Configuration

from .serializers import GeneralMappingSerializer, SubsidiaryMappingSerializer
from .models import GeneralMapping, SubsidiaryMapping
from .tasks import schedule_fyle_attributes_creation, upload_attributes_to_fyle, schedule_cost_centers_creation
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
            configuration = Configuration.objects.get(workspace_id=workspace_id)

            chain = Chain(cached=False)

            if not configuration.auto_map_employees:
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


class MappingSettingsView(ListCreateAPIView):
    """
    Mapping Settings View
    """
    serializer_class = MappingSettingSerializer

    def get_queryset(self):
        return MappingSetting.objects.filter(workspace_id=self.kwargs['workspace_id'])

    def post(self, request, *args, **kwargs):
        """
        Post mapping settings
        """
        try:
            mapping_settings: List[Dict] = request.data

            assert_valid(mapping_settings != [], 'Mapping settings not found')

            all_mapping_settings = []

            for mapping_setting in mapping_settings:
                mapping_setting['source_field'] = mapping_setting['source_field'].upper().replace(' ', '_')

                if 'is_custom' not in mapping_setting:
                    all_mapping_settings.append(mapping_setting)

                if mapping_setting['source_field'] == 'COST_CENTER':
                    schedule_cost_centers_creation(mapping_setting['import_to_fyle'], self.kwargs['workspace_id'])
                    all_mapping_settings.append(mapping_setting)

                if 'is_custom' in mapping_setting and 'import_to_fyle' in mapping_setting and \
                        mapping_setting['source_field'] != 'COST_CENTER':
                    if mapping_setting['import_to_fyle']:
                        upload_attributes_to_fyle(
                            workspace_id=self.kwargs['workspace_id'],
                            netsuite_attribute_type=mapping_setting['destination_field'],
                            fyle_attribute_type=mapping_setting['source_field']
                        )

                    schedule_fyle_attributes_creation(
                        workspace_id=self.kwargs['workspace_id'],
                        netsuite_attribute_type=mapping_setting['destination_field'],
                        import_to_fyle=mapping_setting['import_to_fyle'],
                        fyle_attribute_type=mapping_setting['source_field']
                    )

                    all_mapping_settings.append(mapping_setting)

                    if mapping_setting['destination_field'] == 'PROJECT' and \
                            mapping_setting['import_to_fyle'] is False:
                        schedule: Schedule = Schedule.objects.filter(
                            func='apps.mappings.tasks.auto_create_project_mappings',
                            args='{}'.format(self.kwargs['workspace_id'])
                        ).first()

                        if schedule:
                            schedule.delete()
                            general_settings = Configuration.objects.get(
                                workspace_id=self.kwargs['workspace_id']
                            )
                            general_settings.import_projects = False
                            general_settings.save()

            mapping_settings = MappingSetting.bulk_upsert_mapping_setting(
                all_mapping_settings, self.kwargs['workspace_id']
            )

            return Response(data=self.serializer_class(mapping_settings, many=True).data, status=status.HTTP_200_OK)

        except BulkError as exception:
            logger.error(exception.response)
            return Response(
                data=exception.response,
                status=status.HTTP_400_BAD_REQUEST
            )
