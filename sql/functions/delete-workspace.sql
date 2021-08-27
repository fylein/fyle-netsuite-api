DROP FUNCTION if exists delete_workspace;

CREATE OR REPLACE FUNCTION delete_workspace(IN _workspace_id integer) RETURNS void AS $$
DECLARE
    rcount integer;
BEGIN
    RAISE NOTICE 'Deleting data from workspace %', _workspace_id;

    DELETE
    FROM task_logs tl
    WHERE tl.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % task_logs', rcount;

    DELETE
    FROM bill_lineitems bl
    WHERE bl.bill_id IN (
        SELECT b.id FROM bills b WHERE b.expense_group_id IN (
            SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
        )
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % bill_lineitems', rcount;

    DELETE
    FROM bills b
    WHERE b.expense_group_id IN (
        SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % bills', rcount;

    DELETE
    FROM credit_card_charge_lineitems cccl
    WHERE cccl.credit_card_charge_id IN (
        SELECT ccc.id FROM credit_card_charges ccc WHERE ccc.expense_group_id IN (
            SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
        )
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % credit_card_charge_lineitems', rcount;

    DELETE
    FROM credit_card_charges ccc
    WHERE ccc.expense_group_id IN (
        SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % credit_card_charges', rcount;

    DELETE
    FROM expense_report_lineitems erl
    WHERE erl.expense_report_id IN (
        SELECT er.id FROM expense_reports er WHERE er.expense_group_id IN (
            SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
        )
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % expense_report_lineitems', rcount;

    DELETE
    FROM expense_reports er
    WHERE er.expense_group_id IN (
        SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % expense_reports', rcount;


    DELETE
    FROM journal_entry_lineitems jel
    WHERE jel.journal_entry_id IN (
        SELECT je.id FROM journal_entries je WHERE je.expense_group_id IN (
            SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
        )
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % journal_entry_lineitems', rcount;

    DELETE
    FROM journal_entries je
    WHERE je.expense_group_id IN (
        SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % journal_entries', rcount;

    DELETE
    FROM reimbursements r
    WHERE r.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % reimbursements', rcount;

    DELETE
    FROM expenses e
    WHERE e.id IN (
        SELECT expense_id FROM expense_groups_expenses ege WHERE ege.expensegroup_id IN (
            SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
        )
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % expenses', rcount;

    DELETE
    FROM expense_groups_expenses ege
    WHERE ege.expensegroup_id IN (
        SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % expense_groups_expenses', rcount;

    DELETE
    FROM expense_groups eg
    WHERE eg.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % expense_groups', rcount;

    DELETE
    FROM vendor_payments vp
    WHERE vp.id IN (
        SELECT vpl.vendor_payment_id FROM vendor_payment_lineitems vpl WHERE vpl.expense_group_id IN (
            SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
        )
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % vendor_payments', rcount;

    DELETE
    FROM vendor_payment_lineitems vpl
    WHERE vpl.expense_group_id IN (
        SELECT eg.id FROM expense_groups eg WHERE eg.workspace_id = _workspace_id
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % vendor_payment_lineitems', rcount;

    DELETE
    FROM mappings m
    WHERE m.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % mappings', rcount;

    DELETE
    FROM employee_mappings em
    WHERE em.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % employee_mappings', rcount;

    DELETE
    FROM category_mappings cm
    WHERE cm.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % category_mappings', rcount;

    DELETE
    FROM mapping_settings ms
    WHERE ms.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % mapping_settings', rcount;

    DELETE
    FROM general_mappings gm
    WHERE gm.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % general_mappings', rcount;

    DELETE
    FROM configurations c
    WHERE c.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % configurations', rcount;

    DELETE
    FROM expense_group_settings egs
    WHERE egs.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % expense_group_settings', rcount;

    DELETE
    FROM fyle_credentials fc
    WHERE fc.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % fyle_credentials', rcount;

    DELETE
    FROM netsuite_credentials nc
    WHERE nc.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % netsuite_credentials', rcount;

    DELETE
    FROM expense_attributes ea
    WHERE ea.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % expense_attributes', rcount;

    DELETE
    FROM destination_attributes da
    WHERE da.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % destination_attributes', rcount;

    DELETE
    FROM workspace_schedules wsch
    WHERE wsch.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % workspace_schedules', rcount;

    DELETE
    FROM django_q_schedule dqs
    WHERE dqs.args = _workspace_id::varchar(255);
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % django_q_schedule', rcount;

    DELETE
    FROM auth_tokens aut
    WHERE aut.user_id IN (
        SELECT u.id FROM users u WHERE u.id IN (
            SELECT wu.user_id FROM workspaces_user wu WHERE workspace_id = _workspace_id
        )
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % auth_tokens', rcount;

    DELETE
    FROM workspaces_user wu
    WHERE workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % workspaces_user', rcount;

    DELETE
    FROM subsidiary_mappings sm
    WHERE sm.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % subsidiary_mappings', rcount;

    DELETE
    FROM custom_segments cs
    WHERE cs.workspace_id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % custom_segments', rcount;

    DELETE
    FROM users u
    WHERE u.id IN (
        SELECT wu.user_id FROM workspaces_user wu WHERE workspace_id = _workspace_id
    );
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % users', rcount;

    DELETE
    FROM workspaces w
    WHERE w.id = _workspace_id;
    GET DIAGNOSTICS rcount = ROW_COUNT;
    RAISE NOTICE 'Deleted % workspaces', rcount;

RETURN;
END
$$ LANGUAGE plpgsql;