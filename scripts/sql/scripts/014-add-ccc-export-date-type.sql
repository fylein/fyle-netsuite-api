-- script to add export date type ccc_export_date column in expense_group_settings

rollback;
begin;

-- for spent_at
update expense_group_settings set ccc_export_date_type = 'spent_at' where corporate_credit_card_expense_group_fields::text like '%spent_at%' and not corporate_credit_card_expense_group_fields::text like '%last_spent_at%';


-- for last_spent_at
update expense_group_settings set ccc_export_date_type = 'last_spent_at' where corporate_credit_card_expense_group_fields::text like '%last_spent_at%';


-- for approved_at
update expense_group_settings set ccc_export_date_type = 'approved_at' where corporate_credit_card_expense_group_fields::text like '%approved_at%';


-- set export_date to spent_at for CREDIT CARD CHARGE configuration
update expense_group_settings set ccc_export_date_type = 'spent_at' where workspace_id in (select workspace_id from configurations where corporate_credit_card_expenses_object = 'CREDIT CARD CHARGE');