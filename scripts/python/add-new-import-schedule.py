from django.db import transaction
from django_q.models import Schedule


existing_import_schedules = (
    Schedule.objects.filter(
        func__in=[
            'apps.mappings.tasks.auto_import_and_map_fyle_fields',
            'apps.mappings.tasks.auto_create_tax_codes_mappings',
            'apps.mappings.tasks.async_auto_create_custom_field_mappings',
            'apps.mappings.tasks.auto_create_cost_center_mappings'
        ]
    ).values('args').distinct()
)

try:
    with transaction.atomic():
        for schedule in existing_import_schedules:
            workspace_id = schedule['args']
            is_new_schedule_created = Schedule.objects.filter(
                func='apps.mappings.queue.construct_tasks_and_chain_import_fields_to_fyle',
                args=workspace_id
            ).exists()
            if not is_new_schedule_created:
                old_schedule = Schedule.objects.filter(
                    args=workspace_id
                ).first()
                Schedule.objects.create(
                    func='apps.mappings.queue.construct_tasks_and_chain_import_fields_to_fyle',
                    args=workspace_id,
                    schedule_type=Schedule.MINUTES,
                    minutes=24 * 60,
                    next_run=old_schedule.next_run
                )
        new_schedule = Schedule.objects.filter(
            func='apps.mappings.queue.construct_tasks_and_chain_import_fields_to_fyle'
        ).count()
        print(f"Number of schedules created {new_schedule}")
        raise Exception('Rollback')
except Exception as e:
    print('Error:', e)
