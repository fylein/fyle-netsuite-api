from apps.netsuite.helpers import schedule_payment_sync
from apps.workspaces.models import Configuration, WorkspaceSchedule
from apps.workspaces.tasks import schedule_sync


class AdvancedConfigurationsTriggers:
    """
    Class containing all triggers for advanced_configurations
    """
    @staticmethod
    def run_post_configurations_triggers(workspace_id, workspace_schedule: WorkspaceSchedule, configuration: Configuration):
        """
        Run workspace general settings triggers
        """
        
        schedule_sync(
            workspace_id=workspace_id,
            schedule_enabled=workspace_schedule.get('enabled'),
            hours=workspace_schedule.get('interval_hours'),
            email_added=workspace_schedule.get('additional_email_options'),
            emails_selected=workspace_schedule.get('emails_selected')
        )

        schedule_payment_sync(configuration=configuration)
