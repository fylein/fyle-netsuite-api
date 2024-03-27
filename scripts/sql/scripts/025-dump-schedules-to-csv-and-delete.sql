rollback;
begin;

create temp table old_schedules as (
    select * from django_q_schedule
    where func in (
        'apps.mappings.tasks.auto_import_and_map_fyle_fields',
        'apps.mappings.tasks.auto_create_tax_codes_mappings',
        'apps.mappings.tasks.async_auto_create_custom_field_mappings',
        'apps.mappings.tasks.auto_create_cost_center_mappings'
    )
);

\copy (select * from old_schedules) to '/tmp/django_q_schedule.csv' with csv header;

delete from django_q_schedule
where func in (
    'apps.mappings.tasks.auto_import_and_map_fyle_fields',
    'apps.mappings.tasks.auto_create_tax_codes_mappings',
    'apps.mappings.tasks.async_auto_create_custom_field_mappings',
    'apps.mappings.tasks.auto_create_cost_center_mappings'
);