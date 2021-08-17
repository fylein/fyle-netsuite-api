-- View to help migrate category mappings from mappings table to category_mappings table
drop view if exists category_mappings_view_temp;
drop view if exists category_mappings_view;

create or replace view category_mappings_view_temp as
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

create or replace view category_mappings_view as
select
    cm.source_category_id,
    ndeh.id as destination_expense_head_id,
    nda.id as destination_account_id,
    cm.workspace_id,
    cm.created_at as created_at,
    cm.updated_at as updated_at
from
    category_mappings_view_temp cm
left join destination_attributes da on cm.destination_account_id = da.id
left join destination_attributes nda on (
    da.destination_id =  nda.destination_id and nda.attribute_type = 'ACCOUNT' and nda.workspace_id = da.workspace_id
)
left join destination_attributes deh on cm.destination_expense_head_id = deh.id
left join destination_attributes ndeh on (
    deh.destination_id = ndeh.destination_id and ndeh.attribute_type = 'EXPENSE_CATEGORY' and ndeh.workspace_id = deh.workspace_id
)
where da.attribute_type in ('CCC_ACCOUNT', 'ACCOUNT')
or deh.attribute_type in ('CCC_EXPENSE_CATEGORY', 'EXPENSE_CATEGORY');


-- Checking for any mismatching expense head names in old and new view
select count(*) from category_mappings_view cm
left join category_mappings_view_temp cmt on cm.source_category_id = cmt.source_category_id
left join destination_attributes newda on newda.id = cm.destination_expense_head_id
left join destination_attributes oldda on oldda.id = cmt.destination_expense_head_id
where newda.value <> oldda.value;


-- Checking for any mismatching account names in old and new view
select count(*) from category_mappings_view cm
left join category_mappings_view_temp cmt on cm.source_category_id = cmt.source_category_id
left join destination_attributes newda on newda.id = cm.destination_account_id
left join destination_attributes oldda on oldda.id = cmt.destination_account_id
where newda.value <> oldda.value;


--- Columns which have both expense_head_id and account_id are equal
select count(*) from category_mappings_view_temp
where destination_expense_head_id is not null and destination_account_id is not null;

select count(*) from category_mappings_view
where destination_expense_head_id is not null and destination_account_id is not null;


--- Same number of destination_account
select count(*) from category_mappings_view_temp where destination_account_id is not null;
select count(*) from category_mappings_view where destination_account_id is not null;


--- Same number of destination_expense_head
select count(*) from category_mappings_view_temp where destination_expense_head_id is not null;
select count(*) from category_mappings_view where destination_expense_head_id is not null;


--- No CCC_ACCOUNT in the new view
select count(*) from (
    select cm.destination_expense_head_id, cm.destination_account_id, da.value, da.attribute_type
    from category_mappings_view cm left join destination_attributes da on cm.destination_account_id = da.id
    where da.attribute_type = 'CCC_ACCOUNT'
) s;


--- No CCC_EXPENSE_CATEGORY in the new view
select count(*) from (
    select cm.destination_expense_head_id, cm.destination_account_id, da.value, da.attribute_type
    from category_mappings_view cm left join destination_attributes da on cm.destination_expense_head_id = da.id
    where da.attribute_type = 'CCC_EXPENSE_CATEGORY'
) s;


--- No of rows match
select count(*) from category_mappings_view_temp;
select count(*) from category_mappings_view;