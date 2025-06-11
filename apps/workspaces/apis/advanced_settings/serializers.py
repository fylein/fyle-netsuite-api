from rest_framework import serializers
from django_q.tasks import async_task

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
            'auto_create_merchants',
            'memo_structure',
            'je_single_credit_line'
        ]


class GeneralMappingsSerializer(serializers.ModelSerializer):

    netsuite_location = ReadWriteSerializerMethodField()
    netsuite_location_level = ReadWriteSerializerMethodField()
    netsuite_department = ReadWriteSerializerMethodField()
    netsuite_department_level = ReadWriteSerializerMethodField()
    netsuite_class = ReadWriteSerializerMethodField()
    netsuite_class_level = ReadWriteSerializerMethodField()
    use_employee_location = ReadWriteSerializerMethodField()
    use_employee_department = ReadWriteSerializerMethodField()
    use_employee_class = ReadWriteSerializerMethodField()
    vendor_payment_account = ReadWriteSerializerMethodField()

    class Meta:
        model = GeneralMapping
        fields = [
            'vendor_payment_account',
            'netsuite_location',
            'netsuite_location_level',
            'netsuite_department',
            'netsuite_department_level',
            'netsuite_class',
            'netsuite_class_level',
            'use_employee_location',
            'use_employee_department',
            'use_employee_class'
        ]

    def get_vendor_payment_account(self, instance: GeneralMapping):
        return {
            'name': instance.vendor_payment_account_name,
            'id': instance.vendor_payment_account_id
        }

    def get_netsuite_location(self, instance: GeneralMapping):
        return {
            'name': instance.location_name,
            'id': instance.location_id
        }

    def get_netsuite_location_level(self, instance: GeneralMapping):
        return instance.location_level

    def get_netsuite_department(self, instance: GeneralMapping):
        return {
            'name': instance.department_name,
            'id': instance.department_id
        }
 
    def get_netsuite_department_level(self, instance: GeneralMapping):
        return instance.department_level

    def get_netsuite_class(self, instance: GeneralMapping):
        return {
            'name': instance.class_name,
            'id': instance.class_id
        }

    def get_netsuite_class_level(self, instance: GeneralMapping):
        return instance.class_level 

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
            'emails_selected',
            'is_real_time_export_enabled'
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
                'auto_create_merchants': configurations.get('auto_create_merchants'),
                'change_accounting_period': configurations.get('change_accounting_period'),
                'memo_structure': configurations.get('memo_structure'),
                'je_single_credit_line': configurations.get('je_single_credit_line')
            }
        )
        
        GeneralMapping.objects.update_or_create(
            workspace=instance,
            defaults={
                'vendor_payment_account_id': general_mappings.get('vendor_payment_account').get('id'),
                'vendor_payment_account_name': general_mappings.get('vendor_payment_account').get('name'),
                'location_id': general_mappings.get('netsuite_location').get('id'),
                'location_name': general_mappings.get('netsuite_location').get('name'),
                'department_id': general_mappings.get('netsuite_department').get('id'),
                'department_name': general_mappings.get('netsuite_department').get('name'),
                'class_id': general_mappings.get('netsuite_class').get('id'),
                'class_name': general_mappings.get('netsuite_class').get('name'),
                'location_level': general_mappings.get('netsuite_location_level'),
                'department_level': general_mappings.get('netsuite_department_level'),
                'class_level': general_mappings.get('netsuite_class_level'),
                'use_employee_location': general_mappings.get('use_employee_location'),
                'use_employee_department': general_mappings.get('use_employee_department'),
                'use_employee_class': general_mappings.get('use_employee_class')
            }
        )

        AdvancedConfigurationsTriggers.run_post_configurations_triggers(instance.id, workspace_schedule=workspace_schedules, configuration=configuration_instance)

        if instance.onboarding_state == 'ADVANCED_CONFIGURATION':
            instance.onboarding_state = 'COMPLETE'
            instance.save()

            AdvancedConfigurationsTriggers.post_to_integration_settings(instance.id, True)
            async_task('apps.workspaces.tasks.async_create_admin_subcriptions', instance.id)

        return instance
    
    def validate(self, data):
        if not data.get('configuration'):
            raise serializers.ValidationError('Configurations are required')

        if not data.get('general_mappings'):
            raise serializers.ValidationError('General mappings are required')

        if not data.get('workspace_schedules'):
            raise serializers.ValidationError('Workspace Schedules are required')

        return data
