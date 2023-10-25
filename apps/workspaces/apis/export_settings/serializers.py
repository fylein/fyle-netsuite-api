from apps.fyle.models import ExpenseGroupSettings
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import Configuration, Workspace
from rest_framework import serializers

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

class ConfigurationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Configuration
        fields = [
            'reimbursable_expenses_object',
            'corporate_credit_card_expenses_object',
            'is_simplify_report_closure_enabled',
            'name_in_journal_entry',
            'auto_map_employees',
            'employee_field_mapping'
        ]

        read_only_fields = ['is_simplify_report_closure_enabled']   

class GeneralMappingsSerializer(serializers.ModelSerializer):
    reimbursable_account = ReadWriteSerializerMethodField()
    default_ccc_account = ReadWriteSerializerMethodField()
    accounts_payable = ReadWriteSerializerMethodField()
    default_ccc_vendor = ReadWriteSerializerMethodField()

    class Meta:
        model = GeneralMapping
        fields = [
            'reimbursable_account',
            'default_ccc_account',
            'accounts_payable',
            'default_ccc_vendor',
        ]

    def get_reimbursable_account(self, instance: GeneralMapping):
        return {
            'id': instance.reimbursable_account_id,
            'name': instance.reimbursable_account_name 
        }
    def get_default_ccc_account(self, instance: GeneralMapping):
        return {
            'id': instance.default_ccc_account_id,
            'name': instance.default_ccc_account_name
        }
    def get_accounts_payable(self, instance: GeneralMapping):
        return {
            'id': instance.accounts_payable_id,
            'name': instance.accounts_payable_name
        }
    def get_default_ccc_vendor(self, instance: GeneralMapping):
        return {
            'id': instance.default_ccc_vendor_id,
            'name': instance.default_ccc_vendor_name
        }

class ExpenseGroupSettingsSerializer(serializers.ModelSerializer):
    reimbursable_expense_group_fields = serializers.ListField(allow_null=True, required=False)
    reimbursable_export_date_type = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    expense_state = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    corporate_credit_card_expense_group_fields = serializers.ListField(allow_null=True, required=False)
    ccc_export_date_type = serializers.CharField(allow_null=True, allow_blank=True, required=False) 
    ccc_expense_state = serializers.CharField(allow_null=True, allow_blank=True, required=False)

    class Meta:
        model = ExpenseGroupSettings
        fields = [
            'reimbursable_expense_group_fields',
            'reimbursable_export_date_type',
            'expense_state',
            'corporate_credit_card_expense_group_fields',
            'ccc_export_date_type',
            'ccc_expense_state'
        ]


class ExportSettingsSerializer(serializers.ModelSerializer):
    expense_group_settings = ExpenseGroupSettingsSerializer()
    configuration = ConfigurationSerializer()
    general_mappings = GeneralMappingsSerializer()
    workspace_id = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'expense_group_settings',
            'configuration',
            'general_mappings',
            'workspace_id'
        ]
        read_only_fields = ['workspace_id']


    def get_workspace_id(self, instance):
        return instance.id

    def update(self, instance: Workspace, validated_data):

        configurations = validated_data.pop('configuration')
        expense_group_settings = validated_data.pop('expense_group_settings')
        general_mappings = validated_data.pop('general_mappings')
        workspace_id = instance.id

        Configuration.objects.update_or_create(
            workspace_id=workspace_id,
            defaults={
                'reimbursable_expenses_object': configurations['reimbursable_expenses_object'], 
                'corporate_credit_card_expenses_object': configurations['corporate_credit_card_expenses_object'],
                'employee_field_mapping': configurations['employee_field_mapping']
            }
        )

        if not expense_group_settings['reimbursable_expense_group_fields']:
            expense_group_settings['reimbursable_expense_group_fields'] = ['employee_email', 'report_id', 'fund_source', 'claim_number']

        if not expense_group_settings['corporate_credit_card_expense_group_fields']:
            expense_group_settings['corporate_credit_card_expense_group_fields'] = ['employee_email', 'report_id', 'fund_source', 'claim_number']

        if not expense_group_settings['reimbursable_export_date_type']:
            expense_group_settings['reimbursable_export_date_type'] = 'current_date'

        if not expense_group_settings['ccc_export_date_type']:
            expense_group_settings['ccc_export_date_type'] = 'current_date'

        ExpenseGroupSettings.update_expense_group_settings(expense_group_settings, workspace_id=workspace_id)

        GeneralMapping.objects.update_or_create(
            workspace = instance,
            defaults={
                'reimbursable_account_id': general_mappings['reimbursable_account']['id'],
                'reimbursable_account_name': general_mappings['reimbursable_account']['name'],
                'default_ccc_account_id': general_mappings['default_ccc_account']['id'],
                'default_ccc_account_name': general_mappings['default_ccc_account']['name'],
                'accounts_payable_id': general_mappings['accounts_payable']['id'],
                'accounts_payable_name': general_mappings['accounts_payable']['name'],
                'default_ccc_vendor_id': general_mappings['default_ccc_vendor']['id'],
                'default_ccc_vendor_name': general_mappings['default_ccc_vendor']['name']
            }
        )

        if instance.onboarding_state == 'EXPORT_SETTINGS':
            instance.onboarding_state = 'IMPORT_SETTINGS'
            instance.save()
        
        return instance

    def validate(self, data):

        if not data.get('expense_group_settings'):
            raise serializers.ValidationError('Expense group settings are required')
        
        if not data.get('configuration'):
            raise serializers.ValidationError('Configurations settings are required')
            
        if not data.get('general_mappings'):
            raise serializers.ValidationError('General mappings are required')

        return data
