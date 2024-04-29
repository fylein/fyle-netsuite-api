rollback;
begin;

update workspaces
set last_synced_at = (
	select max(case when e.fund_source = 'PERSONAL' then e.created_at end)
	from expenses e
	where 
	e.fund_source = 'PERSONAL'
	and 
	e.workspace_id = workspaces.id
	group by e.workspace_id
),
ccc_last_synced_at = (
	select max(case when e.fund_source = 'CCC' then e.created_at end)
	from expenses e
	where 
	e.fund_source = 'CCC'
	and 
	e.workspace_id = workspaces.id
	group by e.workspace_id
)
where workspaces.last_synced_at is null and workspaces.ccc_last_synced_at is null;