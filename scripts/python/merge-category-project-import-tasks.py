from django.db.models import Count
from django.db import transaction
from django_q.models import Schedule

# TODO: take a backup of the schedules table before running this script

# grouping by workspace_id
existing_import_enabled_schedules = Schedule.objects.filter(
    func__in=['apps.mappings.tasks.auto_create_category_mappings', 'apps.mappings.tasks.auto_create_project_mappings', 'apps.mappings.tasks.auto_create_vendors_as_merchants']
).values('args').annotate(workspace_id=Count('args'))

try:
    # Create new schedules and delete the old ones in a transaction block
    with transaction.atomic():
        for schedule in existing_import_enabled_schedules:
            is_new_schedule_created = Schedule.objects.filter(func='apps.mappings.tasks.auto_import_and_map_fyle_fields', args=schedule['args']).count()
            if is_new_schedule_created == 0:
                first_schedule = Schedule.objects.filter(args=schedule['args']).first()
                Schedule.objects.create(
                    func='apps.mappings.tasks.auto_import_and_map_fyle_fields',
                    args=schedule['args'],
                    schedule_type= Schedule.MINUTES,
                    minutes=24 * 60,
                    next_run=first_schedule.next_run
                )


        # Delete the old schedules
        Schedule.objects.filter(
            func__in=['apps.mappings.tasks.auto_create_category_mappings', 'apps.mappings.tasks.auto_create_project_mappings', 'apps.mappings.tasks.auto_create_vendors_as_merchants']
        ).delete()
    
except Exception as e:
    print(e)
