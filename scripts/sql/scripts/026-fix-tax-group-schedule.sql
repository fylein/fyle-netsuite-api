rollback;
begin;

create temp table old_schedules as (
    select * from django_q_schedule
    where func in (
        'apps.mappings.tasks.auto_create_tax_group_mappings',
    )
);

\copy (select * from old_schedules) to '/tmp/django_q_schedule.csv' with csv header;

delete from django_q_schedule
where func in (
    'apps.mappings.tasks.auto_create_tax_group_mappings',
);