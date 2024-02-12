rollback;
begin;

update expenses set accounting_export_summary = jsonb_build_object(
    'id', expense_id,
    'url', 'https://staging1.fyle.tech/app/settings/#/integrations/native_apps?integrationIframeTarget=integrations/intacct/workspaces/main/export_log',
    'state', 'SKIPPED',
    'synced', false,
    'error_type', null
) where is_skipped = 't';
