from apps.mappings.models import GeneralMapping
from apps.workspaces.apis.import_settings.triggers import ImportSettingsTrigger
from rest_framework import serializers
from fyle_accounting_mappings.models import MappingSetting
from django.db import transaction
from django.db.models import Q

from apps.workspaces.models import Workspace, Configuration


class MappingSettingFilteredListSerializer(serializers.ListSerializer):
    """
    Serializer to filter the active system, which is a boolen field in
    System Model. The value argument to to_representation() method is
    the model instance
    """
    def to_representation(self, data):
        data = data.filter(~Q(
            destination_field__in=[
                'ACCOUNT',
                'CCC_ACCOUNT',
                'BANK_ACCOUNT',
                'CREDIT_CARD_ACCOUNT',
                'CHARGE_CARD_NUMBER',
                'ACCOUNTS_PAYABLE',
                'VENDOR_PAYMENT_ACCOUNT'
                'EMPLOYEE',
                'EXPENSE_TYPE',
                'TAX_DETAIL',
                'VENDOR',
                'CURRENCY',
                'SUBSIDIARY',
            ])
        )
        return super(MappingSettingFilteredListSerializer, self).to_representation(data)


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
        return {
            self.field_name: data
        }


class MappingSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MappingSetting
        list_serializer_class = MappingSettingFilteredListSerializer
        fields = [
            'source_field',
            'destination_field',
            'import_to_fyle',
            'is_custom',
            'source_placeholder'
        ]


class ConfigurationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        fields = [
            'import_categories',
            'import_vendors_as_merchants',
            'import_items',
            'import_tax_items',
            'import_netsuite_employees'
        ]

class GeneralMappingsSerializer(serializers.ModelSerializer):
    default_tax_code = ReadWriteSerializerMethodField()

    class Meta:
        model = GeneralMapping
        fields = ["default_tax_code"]

    def get_default_tax_code(self, instance):
        return {
            "name": instance.default_tax_code_name,
            "id": instance.default_tax_code_id,
        }


class ImportSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for the ImportSettings Form/API
    """

    configuration = ConfigurationsSerializer()
    general_mappings = GeneralMappingsSerializer()
    mapping_settings = MappingSettingSerializer(many=True)
    workspace_id = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['configuration', 'general_mappings','mapping_settings', 'workspace_id']
        read_only_fields = ['workspace_id']

    def get_workspace_id(self, instance):
        return instance.id

    def update(self, instance, validated_data):

        configurations = validated_data.pop('configuration')
        mapping_settings = validated_data.pop('mapping_settings')

        configurations_instance, _ = Configuration.objects.update_or_create(
            workspace=instance,
            defaults={
                'import_categories': configurations.get('import_categories'),
                'import_items': configurations.get('import_items'),
                'import_tax_items': configurations.get('import_tax_items'),
                'import_vendors_as_merchants': configurations.get('import_vendors_as_merchants'),
                'import_netsuite_employees': configurations.get('import_netsuite_employees')
            },
        )

        trigger: ImportSettingsTrigger = ImportSettingsTrigger(configurations=configurations, mapping_settings=mapping_settings, workspace_id=instance.id)

        trigger.post_save_configurations(configurations_instance)
        trigger.pre_save_mapping_settings()

        if configurations['import_tax_items']:
            mapping_settings.append({'source_field': 'TAX_GROUP', 'destination_field': 'TAX_ITEM', 'import_to_fyle': True, 'is_custom': False})

        mapping_settings.append({'source_field': 'CATEGORY', 'destination_field': 'ACCOUNT', 'import_to_fyle': False, 'is_custom': False})

        with transaction.atomic():
            for setting in mapping_settings:
                MappingSetting.objects.update_or_create(
                    destination_field=setting['destination_field'],
                    workspace_id=instance.id,
                    defaults={
                        'source_field': setting['source_field'],
                        'import_to_fyle': setting['import_to_fyle'] if 'import_to_fyle' in setting else False,
                        'is_custom': setting['is_custom'] if 'is_custom' in setting else False,
                        'source_placeholder': setting['source_placeholder'] if 'source_placeholder' in setting else None,
                    },
                )

        trigger.post_save_mapping_settings(configurations_instance)

        if instance.onboarding_state == 'IMPORT_SETTINGS':
            instance.onboarding_state = 'ADVANCED_CONFIGURATION'
            instance.save()

        return instance

    def validate(self, data):
        if not data.get('configuration'):
            raise serializers.ValidationError('Configurations are required')

        if data.get('mapping_settings') is None:
            raise serializers.ValidationError('Mapping settings are required')

        return data
