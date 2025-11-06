import logging
from datetime import datetime

from django_q.tasks import Chain
from django_q.models import Schedule
from fyle_accounting_mappings.models import MappingSetting, ExpenseAttribute

from apps.mappings.tasks import schedule_auto_map_employees, \
    schedule_auto_map_ccc_employees, schedule_netsuite_employee_creation_on_fyle
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import Configuration
from apps.workspaces.tasks import patch_integration_settings_for_unmapped_cards
from apps.mappings.schedules import new_schedule_or_delete_fyle_import_tasks

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def schedule_or_delete_auto_mapping_tasks(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Instance
    :return: None
    """
    new_schedule_or_delete_fyle_import_tasks(configuration, MappingSetting.objects.filter(workspace_id=configuration.workspace_id).values())
    schedule_auto_map_employees(
        employee_mapping_preference=configuration.auto_map_employees, workspace_id=int(configuration.workspace_id))
    schedule_netsuite_employee_creation_on_fyle(
        import_netsuite_employees=configuration.import_netsuite_employees, workspace_id=int(configuration.workspace_id)
    )
    # Delete schedule if auto map is turned off
    if not configuration.auto_map_employees:
        schedule_auto_map_ccc_employees(workspace_id=int(configuration.workspace_id))

def validate_and_trigger_auto_map_employees(workspace_id: int):
    general_mappings = GeneralMapping.objects.filter(workspace_id=workspace_id).first()
    configuration = Configuration.objects.get(workspace_id=workspace_id)

    chain = Chain()

    if configuration.auto_map_employees:
        chain.append('apps.mappings.tasks.async_auto_map_employees', workspace_id, q_options={'cluster': 'import'})

    if general_mappings and general_mappings.default_ccc_account_name:
        chain.append('apps.mappings.tasks.async_auto_map_ccc_account', workspace_id, q_options={'cluster': 'import'})

    chain.run()


def is_auto_sync_allowed(configuration: Configuration, mapping_setting: MappingSetting = None):
    """
    Get the auto sync permission
    :return: bool
    """
    is_auto_sync_status_allowed = False
    if (mapping_setting and mapping_setting.destination_field == 'PROJECT' and mapping_setting.source_field == 'PROJECT') or configuration.import_categories:
        is_auto_sync_status_allowed = True

    return is_auto_sync_status_allowed


def prepend_code_to_name(prepend_code_in_name: bool, value: str, code: str = None) -> str:
    """
    Format the attribute name based on the use_code_in_naming flag
    """
    if prepend_code_in_name and code:
        return "{}: {}".format(code, value)
    return value


def patch_corporate_card_integration_settings(workspace_id: int) -> None:
    """
    Patch integration settings for unmapped corporate cards.
    This is called when corporate card mapping is created or when a corporate card is created via webhook.

    :param workspace_id: Workspace ID
    :return: None
    """
    configuration = Configuration.objects.filter(workspace_id=workspace_id).first()

    if configuration and configuration.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE':
        unmapped_card_count = ExpenseAttribute.objects.filter(
            attribute_type="CORPORATE_CARD", workspace_id=workspace_id, active=True, mapping__isnull=True
        ).count()

        patch_integration_settings_for_unmapped_cards(workspace_id=workspace_id, unmapped_card_count=unmapped_card_count)
        logger.info(f"Patched integration settings for workspace {workspace_id}, unmapped card count: {unmapped_card_count}")
