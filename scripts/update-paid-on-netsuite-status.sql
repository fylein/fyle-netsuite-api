-- Script to set paid_on_netsuite as True for existing bills, expense_reports
rollback;
begin;

-- bills
update bills
set paid_on_netsuite = True
where bills.paid_on_netsuite = False;

-- expense_reports
update expense_reports
set paid_on_netsuite = True
where expense_reports.paid_on_netsuite = False;

-- expenses
update expenses
set paid_on_netsuite = True
where expenses.paid_on_netsuite = False;
