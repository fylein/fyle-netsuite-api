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
    workspace = serializers.CharField()

    def create(self, validated_data):
        """
        Create / Update Configurations
        :param validated_data: Validated data
        :return: upserted configurations object
        """
        workspace = validated_data['workspace']

        configuration, _ = Configuration.objects.update_or_create(
            workspace_id=workspace,
            defaults={
                'employee_field_mapping': validated_data['employee_field_mapping'],
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

    def validate(self, attrs):
        """
        Validate auto create destination entity
        :param attrs: Non-validated data
        :return: upserted general settings object
        """
        if not attrs['auto_map_employees'] and attrs['auto_create_destination_entity']:
            raise serializers.ValidationError(
                'Cannot set auto_create_destination_entity value if auto map employees is disabled')

        if attrs['auto_map_employees'] == 'EMPLOYEE_CODE' and attrs['auto_create_destination_entity']:
            raise serializers.ValidationError('Cannot enable auto create destination entity for employee code')

        if attrs['corporate_credit_card_expenses_object'] and \
            attrs['corporate_credit_card_expenses_object'] != 'CREDIT CARD CHARGE' and attrs['auto_create_merchants']:
            raise serializers.ValidationError('Cannot enable auto create merchants without using CC Charge')

        if attrs['employee_field_mapping'] == 'EMPLOYEE' and attrs['reimbursable_expenses_object'] not in [
            'EXPENSE REPORT', 'JOURNAL ENTRY'
        ]:
            raise serializers.ValidationError(
                'Reimbursable expenses should be expense report or journal entry for employee mapped to employee')

        if attrs['employee_field_mapping'] == 'VENDOR' and attrs['reimbursable_expenses_object'] not in [
            'BILL', 'JOURNAL ENTRY'
        ]:
            raise serializers.ValidationError(
                'Reimbursable expenses should be bill or journal entry for employee mapped to vendor')

        if attrs['corporate_credit_card_expenses_object'] and \
            attrs['corporate_credit_card_expenses_object'] == 'EXPENSE REPORT' \
                and attrs['reimbursable_expenses_object'] != 'EXPENSE REPORT':
            raise serializers.ValidationError(
                'Corporate credit card expenses can be expense report if reimbursable expense object is expense report')

        if (attrs['sync_fyle_to_netsuite_payments'] or attrs['sync_netsuite_to_fyle_payments']) \
            and attrs['reimbursable_expenses_object'] == 'JOURNAL ENTRY':
            raise serializers.ValidationError(
                'Cannot enable sync fyle to netsuite if reimbursable expense object is journal entry'
            )

        return attrs

    class Meta:
        model = Configuration
        fields = '__all__'
