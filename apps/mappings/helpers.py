from datetime import datetime

from django_q.tasks import Chain
from django_q.models import Schedule
from fyle_accounting_mappings.models import MappingSetting

from apps.mappings.tasks import schedule_auto_map_employees, \
    schedule_auto_map_ccc_employees, schedule_tax_groups_creation, schedule_vendors_as_merchants_creation, \
        schedule_netsuite_employee_creation_on_fyle
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import Configuration


def schedule_or_delete_auto_mapping_tasks(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Instance
    :return: None
    """
    schedule_or_delete_fyle_import_tasks(configuration)
    schedule_auto_map_employees(
        employee_mapping_preference=configuration.auto_map_employees, workspace_id=int(configuration.workspace_id))
    schedule_tax_groups_creation(
        import_tax_items=configuration.import_tax_items, workspace_id=int(configuration.workspace_id))
    schedule_vendors_as_merchants_creation(
        import_vendors_as_merchants=configuration.import_vendors_as_merchants, workspace_id = configuration.workspace_id)
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
        chain.append('apps.mappings.tasks.async_auto_map_employees', workspace_id)

    if general_mappings and general_mappings.default_ccc_account_name:
        chain.append('apps.mappings.tasks.async_auto_map_ccc_account', workspace_id)

    chain.run()


def schedule_or_delete_fyle_import_tasks(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Instance
    :return: None
    """
    project_mapping = MappingSetting.objects.filter(source_field='PROJECT', workspace_id=configuration.workspace_id).first()
    if configuration.import_categories or (project_mapping and project_mapping.import_to_fyle) or configuration.import_vendors_as_merchants:
        start_datetime = datetime.now()
        Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_import_and_map_fyle_fields',
            args='{}'.format(configuration.workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': start_datetime
            }
        )
    elif not configuration.import_categories and not (project_mapping and project_mapping.import_to_fyle) and not configuration.import_vendors_as_merchants:
        Schedule.objects.filter(
            func='apps.mappings.tasks.auto_import_and_map_fyle_fields',
            args='{}'.format(configuration.workspace_id)
        ).delete()
