from apps.mappings.tasks import schedule_projects_creation, schedule_categories_creation, schedule_auto_map_employees, \
    schedule_auto_map_ccc_employees
from apps.workspaces.models import Configuration


def schedule_or_delete_auto_mapping_tasks(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Instance
    :return: None
    """
    schedule_projects_creation(import_projects=configuration.import_projects, workspace_id=configuration.workspace_id)
    schedule_categories_creation(
        import_categories=configuration.import_categories, workspace_id=configuration.workspace_id)
    schedule_auto_map_employees(
        employee_mapping_preference=configuration.auto_map_employees, workspace_id=int(configuration.workspace_id))
    schedule_auto_map_ccc_employees(workspace_id=int(configuration.workspace_id))