rollback;
begin;

update mapping_settings
set import_to_fyle = 't'
where source_field = 'PROJECT' and workspace_id in (select workspace_id from configurations where import_projects = 't');