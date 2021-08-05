-- Script to set exported_at to updated_at of bills / journal_entries and expense_reports for existing expense groups
rollback;
begin;

-- expense_reports
update expense_groups
set exported_at = expense_reports.updated_at
from expense_reports 
where expense_reports.expense_group_id = expense_groups.id;

-- journal_entries
update expense_groups
set exported_at = journal_entries.updated_at
from journal_entries 
where journal_entries.expense_group_id = expense_groups.id;

-- bills
update expense_groups
set exported_at = bills.updated_at
from bills 
where bills.expense_group_id = expense_groups.id;
