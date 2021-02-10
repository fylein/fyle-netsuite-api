rollback;
begin;

update destination_attributes set attribute_type = 'EXPENSE_CATEGORY' where display_name = 'Expense Category';
update destination_attributes set attribute_type = 'CCC_EXPENSE_CATEGORY' where display_name = 'Credit Card Expense Category';