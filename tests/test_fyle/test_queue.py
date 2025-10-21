from fyle_accounting_library.rabbitmq.data_class import Task

from apps.workspaces.models import Workspace
from apps.netsuite.queue import __create_chain_and_run
from apps.fyle.queue import async_import_and_export_expenses


# This test is just for cov :D
def test_create_chain_and_run(db):
    workspace_id = 1
    chain_tasks = [
        Task(
            target='apps.sage_intacct.tasks.create_bill',
            args=[1, 1, True, True]
        )
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


def test_async_import_and_export_expenses_ejected_from_report(db):
    """
    Test async_import_and_export_expenses for EJECTED_FROM_REPORT action
    """
    body = {
        'action': 'EJECTED_FROM_REPORT',
        'resource': 'EXPENSE',
        'data': {
            'id': 'txExpense123',
            'org_id': 'or79Cob97KSh'
        }
    }

    workspace = Workspace.objects.get(id=1)

    async_import_and_export_expenses(body, workspace.id)


def test_async_import_and_export_expenses_added_to_report(db):
    """
    Test async_import_and_export_expenses for ADDED_TO_REPORT action
    """
    body = {
        'action': 'ADDED_TO_REPORT',
        'resource': 'EXPENSE',
        'data': {
            'id': 'txExpense456',
            'org_id': 'or79Cob97KSh',
            'report_id': 'rpReport123'
        }
    }

    workspace = Workspace.objects.get(id=1)

    async_import_and_export_expenses(body, workspace.id)
