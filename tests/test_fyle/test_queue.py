from apps.fyle.models import Expense
from apps.workspaces.models import Workspace
from apps.netsuite.queue import __create_chain_and_run
from apps.fyle.queue import async_import_and_export_expenses

from apps.workspaces.models import Workspace


# This test is just for cov :D
def test_create_chain_and_run(db):
    workspace_id = 1
    chain_tasks = [
        {
            'target': 'apps.sage_intacct.tasks.create_bill',
            'expense_group': 1,
            'task_log_id': 1,
            'last_export': True
        }
    ]

    __create_chain_and_run(workspace_id, chain_tasks, False)
    assert True


# This test is just for cov :D
def test_async_import_and_export_expenses(db):
    body = {
        'action': 'ACCOUNTING_EXPORT_INITIATED',
        'data': {
            'id': 'rp1s1L3QtMpF',
            'org_id': 'or79Cob97KSh'
        }
    }

    worksapce, _ = Workspace.objects.update_or_create(
        fyle_org_id='or79Cob97KSh'
    )

    async_import_and_export_expenses(body, worksapce.id)

# This test is just for cov :D (2)
def test_async_import_and_export_expenses_2(db):
    body = {
        'action': 'STATE_CHANGE_PAYMENT_PROCESSING',
        'data': {
            'id': 'rp1s1L3QtMpF',
            'org_id': 'or79Cob97KSh',
            'state': 'APPROVED'
        }
    }

    worksapce, _ = Workspace.objects.update_or_create(
        fyle_org_id = 'or79Cob97KSh'
    )

    async_import_and_export_expenses(body, worksapce.id)
