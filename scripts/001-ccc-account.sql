rollback;
begin;

delete from fyle_accounting_mappings_mappingsetting
    where source_field = 'CATEGORY' and destination_field = 'CCC_ACCOUNT';

insert into fyle_accounting_mappings_mappingsetting(source_field,
    destination_field, created_at, updated_at, workspace_id)
select
    'CATEGORY' as source_field,
    'CCC_ACCOUNT' as destination_field,
    now() as created_at,
    now() as updated_at,
    mappings.workspace_id as workspace_id
from fyle_accounting_mappings_mappingsetting mappings
where mappings.source_field = 'CATEGORY';