-- View to help migrate category mappings from mappings table to category_mappings table
drop view if exists category_mappings_view;

create or replace view category_mappings_view as
select
    m.source_id as source_category_id,
    max(
            case when m.destination_type in ('EXPENSE_CATEGORY', 'CCC_EXPENSE_CATEGORY') then m.destination_id else null end
        ) as destination_expense_head_id,
    max(
            case when m.destination_type in ('ACCOUNT', 'CCC_ACCOUNT') then m.destination_id else null end
        ) as destination_account_id,
    m.workspace_id as workspace_id,
    max(m.created_at) as created_at,
    max(m.updated_at) as updated_at
from
    mappings m
where m.source_type = 'CATEGORY'
group by
    m.source_id, m.workspace_id;