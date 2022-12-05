rollback;
begin;

update 
  expense_group_settings 
set 
  ccc_expense_state = expense_group_settings.expense_state;
