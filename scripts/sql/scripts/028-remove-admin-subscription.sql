\copy (
    select fyle_org_id from workspaces where onboarding_state == 'COMPLETE'
) to '/Users/hrishabh/Desktop/orgs_netsuite.csv' WITH CSV HEADER;



-- Fyle DB
rollback;
begin;

create temp table temp_orgs (
    org_id TEXT
)

--- update path here
\copy temp_orgs (org_id)
from '/Users/hrishabh/Desktop/orgs_netsuite.csv' WITH CSV HEADER;


update platform_schema.admin_subscriptions set is_enabled = 'f' where org_id not in (
    select org_id from temp_orgs
) 
and is_enabled = 't' 
and webhook_url ilike '%netsuite-api%';