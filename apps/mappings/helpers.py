from datetime import datetime

from django_q.tasks import Chain
from django_q.models import Schedule
from fyle_accounting_mappings.models import MappingSetting

from apps.mappings.tasks import schedule_auto_map_employees, \
    schedule_auto_map_ccc_employees, schedule_netsuite_employee_creation_on_fyle
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import Configuration
from apps.mappings.schedules import new_schedule_or_delete_fyle_import_tasks


def schedule_or_delete_auto_mapping_tasks(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Instance
    :return: None
    """
    schedule_or_delete_fyle_import_tasks(configuration)
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


def schedule_or_delete_fyle_import_tasks(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Instance
    :return: None
    """
    if configuration.import_vendors_as_merchants:
        start_datetime = datetime.now()
        Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_import_and_map_fyle_fields',
            cluster='import',
            args='{}'.format(configuration.workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': start_datetime
            }
        )
    elif not configuration.import_vendors_as_merchants:
        Schedule.objects.filter(
            func='apps.mappings.tasks.auto_import_and_map_fyle_fields',
            args='{}'.format(configuration.workspace_id)
        ).delete()


def is_auto_sync_allowed(configuration: Configuration, mapping_setting: MappingSetting = None):
    """
    Get the auto sync permission
    :return: bool
    """
    is_auto_sync_status_allowed = False
    if (mapping_setting and mapping_setting.destination_field == 'CUSTOMER' and mapping_setting.source_field == 'PROJECT') or configuration.import_categories:
        is_auto_sync_status_allowed = True

    return is_auto_sync_status_allowed
