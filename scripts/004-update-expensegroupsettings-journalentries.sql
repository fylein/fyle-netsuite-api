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
