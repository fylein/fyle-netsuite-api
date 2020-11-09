rollback;
begin;

delete from general_mappings where workspace_id = 28;
delete from fyle_accounting_mappings_mapping where workspace_id = 28;
delete from fyle_accounting_mappings_mappingsetting where workspace_id = 28;
delete from workspaces_workspacegeneralsettings where workspace_id = 28;

delete from expense_report_lineitems where expense_report_id in (
    select er.id
    from expense_reports er
    left join expense_groups eg on er.expense_group_id = eg.id
    where eg.workspace_id = 28
);

delete from expense_reports where id in (
    select er.id
    from expense_reports er
    left join expense_groups eg on er.expense_group_id = eg.id
    where eg.workspace_id = 28
);

delete from bill_lineitems where bill_id in (
    select bills.id
    from bills
    left join expense_groups eg on bills.expense_group_id = eg.id
    where eg.workspace_id = 28
);

delete from bills where id in (
    select bills.id
    from expense_reports er
    left join expense_groups eg on bills.expense_group_id = eg.id
    where eg.workspace_id = 28
);

delete from journal_entry_lineitems where journal_entry_id in (
    select journal_entries.id
    from journal_entries
    left join expense_groups eg on journal_entries.expense_group_id = eg.id
    where eg.workspace_id = 28
);

delete from journal_entries where id in (
    select journal_entries.id
    from expense_reports er
    left join expense_groups eg on journal_entries.expense_group_id = eg.id
    where eg.workspace_id = 28
);

delete from task_log where expense_group_id in (
    select id from expense_groups where workspace_id = 28
);

delete from expense_groups_expenses where expensegroup_id in (
    select id from expense_groups where workspace_id = 28
);

delete from expense_groups where workspace_id = 28;

update workspaces set last_synced_at = null where id = 28;