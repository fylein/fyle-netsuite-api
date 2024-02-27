rollback;
begin;

update expenses set accounting_export_summary = jsonb_build_object(
    'id', expense_id,
    'url', CONCAT('https://netsuite.fyleapps.com/workspaces/', workspace_id, '/expense_groups?page_number=0&page_size=10&state=SKIP'),
    'state', 'SKIPPED',
    'synced', false,
    'error_type', null
) where is_skipped = 't';
