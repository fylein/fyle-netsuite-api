rollback;
begin; 

update django_q_schedule 
set next_run = next_run + interval '10 minutes' 
    where id in (
        select x1.id as merchants_next_run 
        from workspaces w inner join (
            select * from django_q_schedule where 
                func = 'apps.mappings.tasks.auto_create_category_mappings'
            ) x1 
        on cast(w.id as text) = x1.args 
        inner join (
            select * from django_q_schedule where 
                func = 'apps.mappings.tasks.auto_create_vendors_as_merchants'
        ) x2 
        on x1.args = x2.args 
        where x1.next_run < x2.next_run
    );
