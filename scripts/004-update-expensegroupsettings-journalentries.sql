rollback;
begin;

-- change expense_state from PAYMENT_PENDING to PAYMENT_PROCESSING
update fyle_expensegroupsettings
set expense_state = 'PAYMENT_PROCESSING'
where fyle_expensegroupsettings.expense_state = 'PAYMENT_PENDING';

-- add entity_id in journal_entries table
update journal_entries
set entity_id = journal_entry_lineitems.entity_id
from journal_entry_lineitems
where journal_entry_lineitems.journal_entry_id = journal_entries.id;

-- Script to set payment_synced as True for existing bills, expense_reports and journal_entries

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
