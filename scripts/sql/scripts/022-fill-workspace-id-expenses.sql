rollback;
begin;

with workspace as (
    select w.fyle_org_id, w.id, e.id as expense_pk from expenses e
    join workspaces w on w.fyle_org_id = e.org_id
)
update expenses e
set workspace_id = w.id
from workspace w
where e.id = w.expense_pk;
