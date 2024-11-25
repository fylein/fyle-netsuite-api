rollback;
begin;

UPDATE expense_group_settings
SET split_expense_grouping = 'SINGLE_LINE_ITEM';
