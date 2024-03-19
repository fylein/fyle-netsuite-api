from rest_framework import serializers

from apps.workspaces.models import Configuration

from .models import GeneralMapping, SubsidiaryMapping
from apps.workspaces.tasks import post_to_integration_settings


class SubsidiaryMappingSerializer(serializers.ModelSerializer):
    """
    Subsidiary mappings group serializer
    """
    class Meta:
        model = SubsidiaryMapping
        fields = '__all__'


class GeneralMappingSerializer(serializers.ModelSerializer):
    """
    General mappings group serializer
    """
    workspace = serializers.CharField()

    def create(self, validated_data):
        """
        Create or Update General Mappings
        :param validated_data: Validated data
        :return: upserted general mappings object
        """
        workspace_id = validated_data.pop('workspace')

        general_mapping_object, is_created = GeneralMapping.objects.update_or_create(
            workspace_id=workspace_id,
            defaults=validated_data
        )
        
        # if is_created:
        #     post_to_integration_settings(workspace_id, True)

        return general_mapping_object

    def validate(self, data):
        """
        Validate auto create destination entity
        :param data: Non-validated data
        :return: upserted general settings object
        """
        configuration = Configuration.objects.get(workspace_id=data['workspace'])

        if (configuration.employee_field_mapping == 'VENDOR' or\
                configuration.corporate_credit_card_expenses_object == 'BILL') and (
                not data['accounts_payable_name'] or not data['accounts_payable_id']):
            raise serializers.ValidationError('Accounts payable is missing')

        if configuration.employee_field_mapping == 'EMPLOYEE' and (
            not data['reimbursable_account_name'] or not data['reimbursable_account_id']):
            raise serializers.ValidationError('Reimbursable account is missing')

        if configuration.corporate_credit_card_expenses_object and\
                configuration.corporate_credit_card_expenses_object != 'BILL' and (
                    not data['default_ccc_account_name'] or not data['default_ccc_account_id']):
            raise serializers.ValidationError('Default CCC account is missing')

        if (configuration.corporate_credit_card_expenses_object == 'BILL' or \
                configuration.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE') and (
                    not data['default_ccc_vendor_name'] or not data['default_ccc_vendor_id']):
            raise serializers.ValidationError('Default CCC vendor is missing')

        if configuration.sync_fyle_to_netsuite_payments and (
            not data['vendor_payment_account_name'] or not data['vendor_payment_account_id']):
            raise serializers.ValidationError('Vendor payment account is missing')

        if configuration.employee_field_mapping != 'EMPLOYEE' and\
                (data['use_employee_department'] or data['use_employee_location'] or data['use_employee_class']):
            raise serializers.ValidationError(
                'use_employee_department or use_employee_location or use_employee_class'
                ' can be used only when employee is mapped to employee'
            )
        if configuration.employee_field_mapping == 'EMPLOYEE' and data['use_employee_department'] and\
                (data['department_level'] is None):
            raise serializers.ValidationError(
                'department_level cannot be null'
            )

        return data

    class Meta:
        model = GeneralMapping
        fields = '__all__'
