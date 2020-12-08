-- Script to set payment_synced as True for existing bills, expense_reports and journal_entries
rollback;
begin;

-- bills
update bills
set payment_synced = True
where bills.payment_synced = False;

-- expense_reports
update expense_reports
set payment_synced = True
where expense_reports.payment_synced = False;

-- journal_entries
update journal_entries
set payment_synced = True
where journal_entries.payment_synced = False;
