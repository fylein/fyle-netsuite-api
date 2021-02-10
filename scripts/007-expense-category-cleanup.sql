rollback;
begin;

insert into mapping_settings(source_field, destination_field, workspace_id, created_at, updated_at)
select
    'CATEGORY' as source_field,
    'EXPENSE_CATEGORY' as destination_field,
    w.id as workspace_id,
    now(),
    now()
from workspaces w;

insert into mapping_settings(source_field, destination_field, workspace_id, created_at, updated_at)
select
    'CATEGORY' as source_field,
    'CCC_EXPENSE_CATEGORY' as destination_field,
    w.id as workspace_id,
    now(),
    now()
from workspaces w;

update destination_attributes set attribute_type = 'EXPENSE_CATEGORY' where display_name = 'Expense Category';

update destination_attributes set attribute_type = 'CCC_EXPENSE_CATEGORY' where display_name = 'Credit Card Expense Category';