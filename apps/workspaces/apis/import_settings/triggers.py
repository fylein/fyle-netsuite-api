from typing import Dict, List

from django.db.models import Q
from fyle_accounting_mappings.models import MappingSetting, ExpenseAttribute

from apps.fyle.models import ExpenseGroupSettings
from apps.mappings.schedules import new_schedule_or_delete_fyle_import_tasks
from apps.workspaces.models import Configuration


class ImportSettingsTrigger:
    """
    All the post save actions of Import Settings API
    """

    def __init__(self, configurations: Dict, mapping_settings: List[Dict], workspace_id):
        self.__configurations = configurations
        self.__mapping_settings = mapping_settings
        self.__workspace_id = workspace_id

    def remove_department_grouping(self, source_field: str):
        configurations: Configuration = Configuration.objects.filter(workspace_id=self.__workspace_id).first()
        expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=self.__workspace_id)

        # Removing Department Source field from Reimbursable settings
        if configurations.reimbursable_expenses_object:
            reimbursable_settings = expense_group_settings.reimbursable_expense_group_fields
            reimbursable_settings.remove(source_field.lower())
            expense_group_settings.reimbursable_expense_group_fields = list(set(reimbursable_settings))

        # Removing Department Source field from Non reimbursable settings
        if configurations.corporate_credit_card_expenses_object:
            corporate_credit_card_settings = list(expense_group_settings.corporate_credit_card_expense_group_fields)
            corporate_credit_card_settings.remove(source_field.lower())
            expense_group_settings.corporate_credit_card_expense_group_fields = list(set(corporate_credit_card_settings))

        expense_group_settings.save()

    def add_department_grouping(self, source_field: str):
        configurations: Configuration = Configuration.objects.filter(workspace_id=self.__workspace_id).first()

        expense_group_settings: ExpenseGroupSettings = ExpenseGroupSettings.objects.get(workspace_id=self.__workspace_id)

        # Adding Department Source field to Reimbursable settings
        reimbursable_settings = expense_group_settings.reimbursable_expense_group_fields

        if configurations.reimbursable_expenses_object != 'JOURNAL_ENTRY':
            reimbursable_settings.append(source_field.lower())
            expense_group_settings.reimbursable_expense_group_fields = list(set(reimbursable_settings))

        # Adding Department Source field to Non reimbursable settings
        corporate_credit_card_settings = list(expense_group_settings.corporate_credit_card_expense_group_fields)

        if configurations.corporate_credit_card_expenses_object != 'JOURNAL_ENTRY':
            corporate_credit_card_settings.append(source_field.lower())
            expense_group_settings.corporate_credit_card_expense_group_fields = list(set(corporate_credit_card_settings))

        expense_group_settings.save()

    def __update_expense_group_settings_for_departments(self):
        """
        Should group expenses by department source field in case the export is journal entries
        """
        department_setting = list(filter(lambda setting: setting['destination_field'] == 'DEPARTMENT', self.__mapping_settings))

        if department_setting:
            department_setting = department_setting[0]

            self.add_department_grouping(department_setting['source_field'])

    def post_save_configurations(self, configurations_instance: Configuration):
        """
        Post save action for workspace general settings
        """
        new_schedule_or_delete_fyle_import_tasks(
            configuration_instance=configurations_instance,
            mapping_settings=self.__mapping_settings
        )

    def __remove_old_department_source_field(self, current_mappings_settings: List[MappingSetting], new_mappings_settings: List[Dict]):
        """
        Should remove Department Source field from Reimbursable settings in case of deletion and updation
        """
        old_department_setting = current_mappings_settings.filter(destination_field='DEPARTMENT').first()

        new_department_setting = list(filter(lambda setting: setting['destination_field'] == 'DEPARTMENT', new_mappings_settings))

        if old_department_setting and new_department_setting and old_department_setting.source_field != new_department_setting[0]['source_field']:
            self.remove_department_grouping(old_department_setting.source_field.lower())

    def __unset_auto_mapped_flag(self, current_mapping_settings: List[MappingSetting], new_mappings_settings: List[Dict]):
        """
        Set the auto_mapped flag to false for the expense_attributes for the attributes
        whose mapping is changed.
        """
        changed_source_fields = []

        for new_setting in new_mappings_settings:
            destination_field = new_setting['destination_field']
            source_field = new_setting['source_field']
            current_setting = current_mapping_settings.filter(destination_field=destination_field).first()
            if current_setting and current_setting.source_field != source_field:
                changed_source_fields.append(source_field)

        ExpenseAttribute.objects.filter(workspace_id=self.__workspace_id, attribute_type__in=changed_source_fields).update(auto_mapped=False)

    def pre_save_mapping_settings(self):
        """
        Post save action for mapping settings
        """
        mapping_settings = self.__mapping_settings

        new_schedule_or_delete_fyle_import_tasks(
            configuration_instance=Configuration.objects.get(workspace_id=self.__workspace_id),
            mapping_settings=mapping_settings
        )

        # Removal of department grouping will be taken care from post_delete() signal

        # Update department mapping to some other Fyle field
        current_mapping_settings = MappingSetting.objects.filter(workspace_id=self.__workspace_id).all()

        self.__remove_old_department_source_field(current_mappings_settings=current_mapping_settings, new_mappings_settings=mapping_settings)
        self.__unset_auto_mapped_flag(current_mapping_settings=current_mapping_settings, new_mappings_settings=mapping_settings)

    def post_save_mapping_settings(self, configurations_instance: Configuration):
        """
        Post save actions for mapping settings
        """
        destination_fields = []
        for setting in self.__mapping_settings:
            destination_fields.append(setting['destination_field'])

        MappingSetting.objects.filter(~Q(destination_field__in=destination_fields), workspace_id=self.__workspace_id).delete()

        self.__update_expense_group_settings_for_departments()

        new_schedule_or_delete_fyle_import_tasks(
            configuration_instance=configurations_instance,
            mapping_settings=self.__mapping_settings
        )
