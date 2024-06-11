-- Create a view for joined on all settings tables to figure out onboarding progress
create or replace view all_settings_view as 
select 
    w.id as workspace_id,
    wgs.id as configuration_id,
    gm.id as general_mappings_id,
    nc.id as netsuite_creds_id,
    sm.id as subsidiary_id
from workspaces w 
left join 
    configurations wgs on w.id = wgs.workspace_id 
left join 
    netsuite_credentials nc on nc.workspace_id = w.id 
left join 
    general_mappings gm on gm.workspace_id = w.id
left join 
    subsidiary_mappings sm on sm.workspace_id = w.id;

begin; -- Start Transaction Block

-- Count of all workspaces where netsuite are present, configuration is present and general mappings are present
select 
    'NC=TRUE, C=TRUE, GM=TRUE, SM=True' as setting, count(*) 
from all_settings_view 
where 
    configuration_id is not null and general_mappings_id is not null and netsuite_creds_id is not null and subsidiary_id is not null;

--- Update all of the above to have onboarding state set to 'COMPLETE'
update workspaces 
set 
    onboarding_state = 'COMPLETE' 
where id in (
    select 
        workspace_id 
    from all_settings_view 
    where 
        configuration_id is not null and general_mappings_id is not null and netsuite_creds_id is not null and subsidiary_id is not null
);

-- Count of all workspaces where netsuite cred is present and general mapping and credentials and subsidiary are not present.
select 
    'NC=TRUE, C=FALSE, GM=FALSE, SM=FALSE' as setting, count(*)
from all_settings_view
where
    configuration_id is null and general_mappings_id is null and netsuite_creds_id is not null and subsidiary_id is null;

-- Update all of the above to have onboarding state set to 'SUBSIDIARY'
update workspaces
set
    onboarding_state = 'SUBSIDIARY'
where id in (
    select
        workspace_id
    from all_settings_view
    where 
        configuration_id is null and general_mappings_id is null and netsuite_creds_id is not null and subsidiary_id is null
);

-- Count of all workspaces where netsuite cred and subsidiary are present, configuration is not present and general mappings are not present
select 
    'NC=TRUE, C=FALSE, GM=FALSE, SM=TRUE' as settings, count(*) 
from all_settings_view 
where 
    configuration_id is null and general_mappings_id is null and netsuite_creds_id is not null and subsidiary_id is not null;

--- Update all of the above to have onboarding state set to 'EXPORT_SETTINGS'
update workspaces 
set 
    onboarding_state = 'EXPORT_SETTINGS' 
where id in (
    select 
        workspace_id 
    from all_settings_view 
    where 
        configuration_id is null and general_mappings_id is null and netsuite_creds_id is not null and subsidiary_id is not null
);


-- Count of all workspaces where netsuite are present, configuration is present, subsidiary is present and general mappings are not present
select 
    'NC=TRUE, C=TRUE, GM=FALSE, SM=TRUE' as settings, count(*) 
from all_settings_view 
where 
    configuration_id is not null and general_mappings_id is null and netsuite_creds_id is not null and subsidiary_id is not null;

--- Update all of the above to have onboarding state set to 'EXPORT_SETTINGS'
update workspaces 
set 
    onboarding_state = 'EXPORT_SETTINGS' 
where id in (
    select 
        workspace_id 
    from all_settings_view 
    where 
        configuration_id is not null and general_mappings_id is null and netsuite_creds_id is not null and subsidiary_id is not null
);


