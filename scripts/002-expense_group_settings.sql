-- Script to add expense groups settings to existing workspaces
rollback;
begin;

insert into fyle_expensegroupsettings(
    reimbursable_expense_group_fields,
    corporate_credit_card_expense_group_fields,
    expense_state,
    export_date_type,
    created_at,
    updated_at,
    workspace_id
) select
   '{"employee_email", "report_id", "claim_number", "fund_source"}' as reimbursable_expense_group_fields,
   '{"employee_email", "report_id", "claim_number", "fund_source"}' as corporate_credit_card_expense_group_fields,
   'PAYMENT_PROCESSING' as expense_state,
   'current_date' as export_date_type,
   now() as created_at,
   now() as updated_at,
   w.id as workspace_id
from workspaces w
left join workspaces_workspacegeneralsettings gs on w.id = gs.workspace_id
order by w.id;