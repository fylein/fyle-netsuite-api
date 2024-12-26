from apps.workspaces.apis.map_employees.triggers import MapEmployeesTriggers
from apps.workspaces.models import Configuration, Workspace
from rest_framework import serializers


class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        fields = ['employee_field_mapping', 'auto_map_employees']


class MapEmployeesSerializer(serializers.ModelSerializer):

    configuration = ConfigurationSerializer()
    workspace_id = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['configuration', 'workspace_id']
        read_only_fields = ['workspace_id']
    
    def get_workspace_id(self, instance):
        return instance.id

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else None

        workspace_id = instance.id
        configuration = validated_data.pop('configuration')

        configuration_instance = Configuration.objects.filter(workspace_id=workspace_id).first()

        if configuration_instance and (configuration_instance.employee_field_mapping != configuration['employee_field_mapping']):
            configuration_instance.reimbursable_expenses_object = None
            configuration_instance.save()
        
        configuration_instance, _ =  Configuration.objects.update_or_create(
            workspace_id=workspace_id, defaults={'employee_field_mapping': configuration['employee_field_mapping'], 'auto_map_employees': configuration['auto_map_employees']},
            user=user
        )

        MapEmployeesTriggers.run_configurations_triggers(configuration=configuration_instance)

        if instance.onboarding_state == 'MAP_EMPLOYEES':
            instance.onboarding_state = 'EXPORT_SETTINGS'
            instance.save()
        
        return instance

    def validate(self,data):
        if not data.get('configuration').get('employee_field_mapping'):
            raise serializers.ValidationError('employee_field_mapping field is required')

        if data.get('configuration').get('auto_map_employees') and data.get('configuration').get('auto_map_employees') not in ['EMAIL', 'NAME', 'EMPLOYEE_CODE']:
            raise serializers.ValidationError('auto_map_employees can have only EMAIL / NAME / EMPLOYEE_CODE')

        return data
