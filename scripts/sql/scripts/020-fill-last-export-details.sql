rollback;
begin;

insert into last_export_details (
  last_exported_at, export_mode, total_expense_groups_count, 
  successful_expense_groups_count, failed_expense_groups_count, 
  created_at, updated_at, workspace_id
) 
select 
  now(), 
  'MANUAL', 
  0, 
  0, 
  0, 
  now(), 
  now(), 
  id 
from 
  workspaces 
where 
  id not in (
    select 
      workspace_id 
    from 
      last_export_details
  );
