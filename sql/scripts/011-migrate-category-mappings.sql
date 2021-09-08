rollback;
begin;

insert into category_mappings(
    created_at, updated_at, destination_expense_head_id, destination_account_id, source_category_id, workspace_id)
select
    created_at,
    updated_at,
    destination_expense_head_id,
    destination_account_id,
    source_category_id,
    workspace_id
from category_mappings_view;