drop view if exists employee_mappings_view;

create or replace view employee_mappings_view as
select
    m.source_id as source_employee_id,
    max(case when m.destination_type = 'EMPLOYEE' then m.destination_id else null end) as destination_employee_id,
    max(case when m.destination_type = 'VENDOR' then m.destination_id else null end) as destination_vendor_id,
    max(case when m.destination_type = 'CREDIT_CARD_ACCOUNT' then m.destination_id else null end) as destination_card_account_id,
    m.workspace_id as workspace_id,
    max(m.created_at) as created_at,
    max(m.updated_at) as updated_at
from
    mappings m
    where m.source_type = 'EMPLOYEE'
group by m.source_id, workspace_id;
