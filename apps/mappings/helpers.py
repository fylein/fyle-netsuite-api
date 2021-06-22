from django_q.models import Schedule

from apps.mappings.tasks import schedule_projects_creation, schedule_categories_creation, schedule_auto_map_employees, \
    schedule_auto_map_ccc_employees, schedule_cost_centers_creation, upload_attributes_to_fyle, \
    schedule_fyle_attributes_creation
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
    if not configuration.auto_map_employees:
        schedule_auto_map_ccc_employees(workspace_id=int(configuration.workspace_id))


def create_mapping_settings(workspace_id, mapping_settings):
    all_mapping_settings = []

    for mapping_setting in mapping_settings:
        mapping_setting['source_field'] = mapping_setting['source_field'].upper().replace(' ', '_')

        if 'is_custom' not in mapping_setting:
            all_mapping_settings.append(mapping_setting)

        if mapping_setting['source_field'] == 'COST_CENTER':
            schedule_cost_centers_creation(mapping_setting['import_to_fyle'], workspace_id)
            all_mapping_settings.append(mapping_setting)

        if 'is_custom' in mapping_setting and 'import_to_fyle' in mapping_setting and \
                mapping_setting['source_field'] != 'COST_CENTER':
            if mapping_setting['import_to_fyle']:
                upload_attributes_to_fyle(
                    workspace_id=workspace_id,
                    netsuite_attribute_type=mapping_setting['destination_field'],
                    fyle_attribute_type=mapping_setting['source_field']
                )

            schedule_fyle_attributes_creation(
                workspace_id=workspace_id,
                netsuite_attribute_type=mapping_setting['destination_field'],
                import_to_fyle=mapping_setting['import_to_fyle'],
                fyle_attribute_type=mapping_setting['source_field']
            )

            all_mapping_settings.append(mapping_setting)

            if mapping_setting['destination_field'] == 'PROJECT' and \
                    mapping_setting['import_to_fyle'] is False:
                schedule: Schedule = Schedule.objects.filter(
                    func='apps.mappings.tasks.auto_create_project_mappings',
                    args='{}'.format(workspace_id)
                ).first()

                if schedule:
                    schedule.delete()
                    general_settings = Configuration.objects.get(
                        workspace_id=workspace_id
                    )
                    general_settings.import_projects = False
                    general_settings.save()

    return all_mapping_settings
