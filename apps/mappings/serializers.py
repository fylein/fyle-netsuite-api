from rest_framework import serializers

from django.db.models import Q

from fyle_accounting_mappings.models import MappingSetting

from apps.workspaces.models import Configuration

from .models import GeneralMapping, SubsidiaryMapping


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

        general_mapping_object, _ = GeneralMapping.objects.update_or_create(
            workspace_id=workspace_id,
            defaults=validated_data
        )

        return general_mapping_object

    def validate(self, data):
        """
        Validate auto create destination entity
        :param data: Non-validated data
        :return: upserted general settings object
        """
        configuration = Configuration.objects.get(workspace_id=data['workspace'])
        mapping_setting = MappingSetting.objects.filter(
            Q(destination_field='VENDOR') | Q(destination_field='EMPLOYEE'),
            source_field='EMPLOYEE', workspace_id=data['workspace']
        ).first()

        if (mapping_setting.destination_field == 'VENDOR' or\
                configuration.corporate_credit_card_expenses_object == 'BILL') and (
                not data['accounts_payable_name'] or not data['accounts_payable_id']):
            raise serializers.ValidationError('Accounts payable is missing')

        if mapping_setting.destination_field == 'EMPLOYEE' and (
            not data['reimbursable_account_name'] or not data['reimbursable_account_id']):
            raise serializers.ValidationError('Reimbursable account is missing')

        if configuration.corporate_credit_card_expenses_object and\
                configuration.corporate_credit_card_expenses_object != 'BILL' and (
                    not data['default_ccc_account_name'] or not data['default_ccc_account_id']):
            raise serializers.ValidationError('Default CCC account is missing')

        if (configuration.corporate_credit_card_expenses_object == 'BILL' or
            (configuration.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE' and
             not configuration.auto_create_merchants)) \
                and (
                    not data['default_ccc_vendor_name'] or not data['default_ccc_vendor_id']):
            raise serializers.ValidationError('Default CCC vendor is missing')

        if configuration.sync_fyle_to_netsuite_payments and (
            not data['vendor_payment_account_name'] or not data['vendor_payment_account_id']):
            raise serializers.ValidationError('Vendor payment account is missing')

        return data

    class Meta:
        model = GeneralMapping
        fields = '__all__'
