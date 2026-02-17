rollback;
begin;

update expenses set accounting_export_summary = jsonb_build_object(
    'id', expense_id,
    'url', CONCAT('https://app.fylehq.com/app/settings/integrations/native_apps?integrationIframeTarget=integrations/netsuite/main/export_log'),
    'state', 'SKIPPED',
    'synced', false,
    'error_type', null
) where is_skipped = 't';
