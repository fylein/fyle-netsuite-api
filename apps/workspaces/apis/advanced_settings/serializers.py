from rest_framework import serializers

from apps.workspaces.models import Configuration, Workspace, WorkspaceSchedule
from apps.mappings.models import GeneralMapping
from apps.workspaces.apis.advanced_settings.triggers import AdvancedConfigurationsTriggers


class ReadWriteSerializerMethodField(serializers.SerializerMethodField):
    """
    Serializer Method Field to Read and Write from values
    Inherits serializers.SerializerMethodField
    """

    def __init__(self, method_name=None, **kwargs):
        self.method_name = method_name
        kwargs['source'] = '*'
        super(serializers.SerializerMethodField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        return {self.field_name: data}


class ConfigurationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Configuration
        fields = [
            'change_accounting_period',
            'sync_fyle_to_netsuite_payments',
            'sync_netsuite_to_fyle_payments',
            'auto_create_destination_entity',
            'memo_structure'
        ]


class GeneralMappingsSerializer(serializers.ModelSerializer):

    netsuite_location = ReadWriteSerializerMethodField()
    netsuite_location_level = ReadWriteSerializerMethodField()
    department_level = ReadWriteSerializerMethodField()
    use_employee_location = ReadWriteSerializerMethodField()
    use_employee_department = ReadWriteSerializerMethodField()
    use_employee_class = ReadWriteSerializerMethodField()

    class Meta:
        model = GeneralMapping
        fields = [
            'netsuite_location',
            'netsuite_location_level',
            'department_level',
            'use_employee_location',
            'use_employee_department',
            'use_employee_class'
        ]


    def get_netsuite_location(self, instance: GeneralMapping):
        return {
            'name': instance.location_name,
            'id': instance.location_id
        }

    def get_netsuite_location_level(self, instance: GeneralMapping):
        return instance.location_level

    def get_department_level(self, instance: GeneralMapping):
        return instance.department_level

    def get_use_employee_location(self, instance: GeneralMapping):
        return instance.use_employee_location
    
    def get_use_employee_department(self, instance: GeneralMapping):
        return instance.use_employee_department

    def get_use_employee_class(self, instance: GeneralMapping):
        return instance.use_employee_class

class WorkspaceSchedulesSerializer(serializers.ModelSerializer):
    emails_selected = serializers.ListField(allow_null=True, required=False)

    class Meta:
        model = WorkspaceSchedule
        fields = [
            'enabled',
            'interval_hours',
            'additional_email_options',
            'emails_selected'
        ]

class AdvancedSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for the Advanced Configurations Form/API
    """
    configuration = ConfigurationSerializer()
    general_mappings = GeneralMappingsSerializer()
    workspace_schedules = WorkspaceSchedulesSerializer()
    workspace_id = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'configuration',
            'general_mappings',
            'workspace_schedules',
            'workspace_id'
        ]
        read_only_fields = ['workspace_id']


    def get_workspace_id(self, instance):
        return instance.id

    def update(self, instance, validated):
        configurations = validated.pop('configuration')
        general_mappings = validated.pop('general_mappings')
        workspace_schedules = validated.pop('workspace_schedules')

        configuration_instance, _  = Configuration.objects.update_or_create(
            workspace=instance,
            defaults={
                'sync_fyle_to_netsuite_payments': configurations.get('sync_fyle_to_netsuite_payments'),
                'sync_netsuite_to_fyle_payments': configurations.get('sync_netsuite_to_fyle_payments'),
                'auto_create_destination_entity': configurations.get('auto_create_destination_entity'),
                'change_accounting_period': configurations.get('change_accounting_period'),
                'memo_structure': configurations.get('memo_structure')
            }
        )
        
        GeneralMapping.objects.update_or_create(
            workspace=instance,
            defaults={
            'netsuite_location': general_mappings.get('netsuite_location'),
            'netsuite_location_level': general_mappings.get('netsuite_location_level'),
            'department_level': general_mappings.get('department_level'),
            'use_employee_location': general_mappings.get('use_employee_location'),
            'use_employee_department': general_mappings.get('use_employee_department'),
            'use_employee_class': general_mappings.get('use_employee_class')
            }
        )

        AdvancedConfigurationsTriggers.run_post_configurations_triggers(instance.id, workspace_schedule=workspace_schedules, configuration=configuration_instance)

        if instance.onboarding_state == 'ADVANCED_CONFIGURATION':
            instance.onboarding_state = 'COMPLETE'
            instance.save()

        return instance
    
    def validate(self, data):
        if not data.get('configuration'):
            raise serializers.ValidationError('Configurations are required')

        if not data.get('general_mappings'):
            raise serializers.ValidationError('General mappings are required')

        if not data.get('workspace_schedules'):
            raise serializers.ValidationError('Workspace Schedules are required')

        return data
