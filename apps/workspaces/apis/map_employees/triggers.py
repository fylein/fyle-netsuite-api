from apps.mappings.tasks import schedule_auto_map_employees
from apps.workspaces.models import Configuration


class MapEmplyeesTriggers:

    @staticmethod
    def run_workspace_general_settings_triggers(configuration: Configuration):

        schedule_auto_map_employees(configuration.auto_map_employees, configuration.workspace.id)
