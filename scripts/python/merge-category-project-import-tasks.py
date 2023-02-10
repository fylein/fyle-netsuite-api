from django.db.models import Count
from django.db import transaction
from django_q.models import Schedule

# TODO: take a backup of the schedules table before running this script

# grouping by workspace_id
existing_import_enabled_schedules = Schedule.objects.filter(
    func__in=['apps.mappings.tasks.auto_create_category_mappings', 'apps.mappings.tasks.auto_create_project_mappings']
).annotate(workspace_id=Count('args'))

try:
    # Create new schedules and delete the old ones in a transaction block
    with transaction.atomic():
        for schedule in existing_import_enabled_schedules:
            Schedule.objects.create(
                func='apps.mappings.tasks.auto_import_categories_and_projects',
                args=schedule.args,
                schedule_type= Schedule.MINUTES,
                minutes=24 * 60,
                next_run=schedule.next_run
            )


        # Delete the old schedules
        Schedule.objects.filter(
            func__in=['apps.mappings.tasks.auto_create_category_mappings', 'apps.mappings.tasks.auto_create_project_mappings']
        ).delete()
    
except Exception as e:
    print(e)
