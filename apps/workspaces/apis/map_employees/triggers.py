from apps.mappings.tasks import schedule_auto_map_employees
from apps.workspaces.models import Configuration


class MapEmployeesTriggers:

    @staticmethod
    def run_configurations_triggers(configuration: Configuration):

        schedule_auto_map_employees(configuration.auto_map_employees, configuration.workspace.id)
