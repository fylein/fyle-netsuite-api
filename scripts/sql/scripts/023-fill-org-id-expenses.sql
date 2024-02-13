rollback;
begin;

with expense_groups as (
    select w.fyle_org_id, e.id from expenses e
    join expense_groups_expenses ege on e.id = ege.expense_id
    join expense_groups eg on eg.id = ege.expensegroup_id
    join workspaces w on w.id = eg.workspace_id
    where e.org_id is null
)
update expenses e
set org_id = eg.fyle_org_id
from expense_groups eg
where e.id = eg.id;
