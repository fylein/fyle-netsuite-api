from datetime import datetime
from typing import List, Dict
from apps.workspaces.models import Configuration
from django_q.models import Schedule
from fyle_accounting_mappings.models import MappingSetting


def new_schedule_or_delete_fyle_import_tasks(
    configuration_instance: Configuration,
    mapping_settings: List[Dict]
):
    """
    Schedule or delete fyle import tasks based on the
    configuration and mapping settings
    :param configuration_instance: Configuration instance
    :param mapping_settings: List of mapping settings
    :return: None
    """
    # short-hand notation, it returns True as soon as it encounters import_to_fyle as True
    task_to_be_scheduled = any(mapping_setting['import_to_fyle'] for mapping_setting in mapping_settings)

    if (
        task_to_be_scheduled
        or configuration_instance.import_tax_items
    ):
        Schedule.objects.update_or_create(
            func='apps.mappings.queue.construct_tasks_and_chain_import_fields_to_fyle',
            args='{}'.format(configuration_instance.workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now(),
                'cluster': 'import'
            }
        )
    else:
        import_fields_count = MappingSetting.objects.filter(
            workspace_id=configuration_instance.workspace_id,
            import_to_fyle=True
        ).count()

        # if there are no import fields, delete the schedule
        if import_fields_count == 0:
            Schedule.objects.filter(
                func='apps.mappings.queue.construct_tasks_and_chain_import_fields_to_fyle',
                args='{}'.format(configuration_instance.workspace_id)
            ).delete()
