rollback;
begin;

update 
  workspaces 
set 
  ccc_last_synced_at = last_synced_at 
where 
  ccc_last_synced_at is null;
