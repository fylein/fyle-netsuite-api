from apps.workspaces.models import Configuration, LastExportDetail
from apps.netsuite.exceptions import update_last_export_details
from fyle_accounting_mappings.models import MappingSetting
from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog, Error


class ExportSettingsTrigger:
    """
    Class containing all triggers for export_settings
    """
    def __init__(self, workspace_id: int, configuration: Configuration):
        self.__workspace_id = workspace_id
        self.__configuration = configuration

    def __delete_or_create_card_mapping_setting(self):
        enable_card_mapping = self.__configuration.corporate_credit_card_expenses_object != 'BILL'

        mapping_setting = MappingSetting.objects.filter(
            source_field='CORPORATE_CARD',
            workspace_id=self.__workspace_id
        ).first()

        if not mapping_setting and enable_card_mapping:
            MappingSetting.objects.update_or_create(
                destination_field='CREDIT_CARD_ACCOUNT',
                workspace_id=self.__workspace_id,
                defaults={
                    'source_field': 'CORPORATE_CARD',
                    'import_to_fyle': False,
                    'is_custom': False
                }
            )
        else:
            if mapping_setting:
                mapping_setting.delete()

    def post_save_configurations(self):
        """
        Run post save action for configurations
        """
        # Delete all task logs and errors for unselected exports
        fund_source = []

        if self.__configuration.reimbursable_expenses_object:
            fund_source.append('PERSONAL')
        if self.__configuration.corporate_credit_card_expenses_object:
            fund_source.append('CCC')

        self.__delete_or_create_card_mapping_setting()

        expense_group_ids = ExpenseGroup.objects.filter(
            workspace_id=self.__workspace_id,
            exported_at__isnull=True
        ).exclude(fund_source__in=fund_source).values_list('id', flat=True)

        if expense_group_ids:
            Error.objects.filter(workspace_id=self.__workspace_id, expense_group_id__in=expense_group_ids).delete()
            TaskLog.objects.filter(workspace_id=self.__workspace_id, expense_group_id__in=expense_group_ids, status__in=['FAILED', 'FATAL']).delete()
            last_export_detail = LastExportDetail.objects.filter(workspace_id=self.__workspace_id).first()
            if last_export_detail.last_exported_at:
                update_last_export_details(self.__workspace_id)
