from django_q.tasks import Chain

from apps.mappings.tasks import schedule_categories_creation, schedule_auto_map_employees, \
    schedule_auto_map_ccc_employees, schedule_tax_groups_creation, schedule_vendors_as_merchants_creation, \
        schedule_netsuite_employee_creation_on_fyle
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import Configuration


def schedule_or_delete_auto_mapping_tasks(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Instance
    :return: None
    """
    schedule_categories_creation(
        import_categories=configuration.import_categories, workspace_id=configuration.workspace_id)
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
