"""
Workspace Serializers
"""
from rest_framework import serializers

from .models import Workspace, FyleCredential, NetSuiteCredentials, WorkspaceSchedule, Configuration


class WorkspaceSerializer(serializers.ModelSerializer):
    """
    Workspace serializer
    """

    class Meta:
        model = Workspace
        fields = '__all__'


class FyleCredentialSerializer(serializers.ModelSerializer):
    """
    Fyle credential serializer
    """

    class Meta:
        model = FyleCredential
        fields = '__all__'


class NetSuiteCredentialSerializer(serializers.ModelSerializer):
    """
    NetSuite credential serializer
    """

    class Meta:
        model = NetSuiteCredentials
        fields = ['id', 'workspace_id', 'ns_account_id', 'created_at', 'updated_at']


class WorkspaceScheduleSerializer(serializers.ModelSerializer):
    """
    Workspace Schedule Serializer
    """
    class Meta:
        model = WorkspaceSchedule
        fields = '__all__'


class ConfigurationSerializer(serializers.ModelSerializer):
    """
    General settings serializer
    """
    def create(self, validated_data):
        """
        Create Workspace General Settings
        :param validated_data: Validated data
        :return: upserted general settings object
        """
        workspace = validated_data['workspace']

        configuration, _ = Configuration.objects.update_or_create(
            workspace=workspace,
            defaults={
                'reimbursable_expenses_object': validated_data['reimbursable_expenses_object'],
                'corporate_credit_card_expenses_object': validated_data['corporate_credit_card_expenses_object'],
                'sync_fyle_to_netsuite_payments': validated_data['sync_fyle_to_netsuite_payments'],
                'sync_netsuite_to_fyle_payments': validated_data['sync_netsuite_to_fyle_payments'],
                'import_projects': validated_data['import_projects'],
                'import_categories': validated_data['import_categories'],
                'auto_map_employees': validated_data['auto_map_employees'],
                'auto_create_merchants': validated_data['auto_create_merchants'],
                'auto_create_destination_entity': validated_data['auto_create_destination_entity']
            }
        )

        return configuration

    def validate(self, data):
        """
        Validate auto create destination entity
        :param data: Non-validated data
        :return: upserted general settings object
        """
        if not data['auto_map_employees'] and data['auto_create_destination_entity']:
            raise serializers.ValidationError(
                'Cannot set auto_create_destination_entity value if auto map employees is disabled')

        if data['auto_map_employees'] == 'EMPLOYEE_CODE' and data['auto_create_destination_entity']:
            raise serializers.ValidationError('Cannot enable auto create destination entity for employee code')

        if data['corporate_credit_card_expenses_object'] != 'CREDIT CARD CHARGE' and data['auto_create_merchants']:
            raise serializers.ValidationError('Cannot enable auto create merchants without using CC Charge')

        return data

    class Meta:
        model = Configuration
        fields = '__all__'
