rollback;
begin;

with ws as (
  select expense_attributes.detail->>'full_name' as expense_attributes_full_name,
    expense_attributes.workspace_id as expense_attributes_workspace_id,
    expense_attributes.value as expense_attribute_email
  from expense_groups
    inner join expense_attributes on expense_attributes.value = expense_groups.description->>'employee_email'
  where expense_groups.workspace_id = expense_attributes.workspace_id
)

update expense_groups
set employee_name = ws.expense_attributes_full_name
from ws
where expense_groups.description->>'employee_email' = ws.expense_attribute_email;


-- Run this in after running the above query.
with ex as (
  select expense_groups.employee_name as employee_name
  from expense_groups
    inner join expense_groups_expenses on expense_groups.id = expense_groups_expenses.expensegroup_id
    inner join expenses on expense_groups_expenses.expense_id = expenses.id
)

update expenses
set employee_name = ex.employee_name
from ex;