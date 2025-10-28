from unittest import mock

from fyle_accounting_library.rabbitmq.data_class import Task
from fyle_accounting_mappings.models import ExpenseAttribute

from apps.workspaces.models import Workspace, FeatureConfig
from apps.netsuite.queue import __create_chain_and_run
from apps.fyle.queue import handle_webhook_callback
from .fixtures import data


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


def test_create_chain_and_run_with_rabbitmq_worker(db):
    workspace_id = 1
    chain_tasks = [
        Task(
            target='apps.sage_intacct.tasks.create_bill',
            args=[1, 1, True, True]
        )
    ]

    feature_config = FeatureConfig.objects.get(workspace_id=workspace_id)
    feature_config.fyle_webhook_sync_enabled = False
    feature_config.save()

    with mock.patch('apps.netsuite.queue.check_interval_and_sync_dimension') as mock_sync:
        __create_chain_and_run(workspace_id, chain_tasks, True)
        mock_sync.assert_called_once_with(workspace_id)


def test_handle_webhook_callback(db):
    workspace = Workspace.objects.get(id=1)
    body = {
        'action': 'ACCOUNTING_EXPORT_INITIATED',
        'data': {
            'id': 'rp1s1L3QtMpF',
            'org_id': workspace.fyle_org_id
        }
    }

    handle_webhook_callback(body, workspace.id)


def test_handle_webhook_callback_2(db):
    workspace = Workspace.objects.get(id=1)
    body = {
        'action': 'STATE_CHANGE_PAYMENT_PROCESSING',
        'data': {
            'id': 'rp1s1L3QtMpF',
            'org_id': workspace.fyle_org_id,
            'state': 'APPROVED'
        }
    }

    handle_webhook_callback(body, workspace.id)


def test_handle_webhook_callback_ejected_from_report(db):
    workspace = Workspace.objects.get(id=1)
    body = {
        'action': 'EJECTED_FROM_REPORT',
        'resource': 'EXPENSE',
        'data': {
            'id': 'txExpense123',
            'org_id': workspace.fyle_org_id
        }
    }

    handle_webhook_callback(body, workspace.id)


def test_handle_webhook_callback_added_to_report(db):
    workspace = Workspace.objects.get(id=1)
    body = {
        'action': 'ADDED_TO_REPORT',
        'resource': 'EXPENSE',
        'data': {
            'id': 'txExpense456',
            'org_id': workspace.fyle_org_id,
            'report_id': 'rpReport123'
        }
    }

    handle_webhook_callback(body, workspace.id)


def test_handle_webhook_callback_attribute_created_disabled(db):
    workspace = Workspace.objects.get(id=1)

    feature_config = FeatureConfig.objects.get(workspace_id=workspace.id)
    feature_config.fyle_webhook_sync_enabled = False
    feature_config.save()

    body = data['webhook_attribute_data']['category_created'].copy()
    body['data'] = body['data'].copy()
    body['data']['org_id'] = workspace.fyle_org_id

    handle_webhook_callback(body, workspace.id)


def test_handle_webhook_callback_attribute_created_enabled(db):
    workspace = Workspace.objects.get(id=1)

    feature_config = FeatureConfig.objects.get(workspace_id=workspace.id)
    feature_config.fyle_webhook_sync_enabled = True
    feature_config.save()

    body = data['webhook_attribute_data']['category_created'].copy()
    body['data'] = body['data'].copy()
    body['data']['org_id'] = workspace.fyle_org_id

    initial_count = ExpenseAttribute.objects.filter(
        workspace_id=workspace.id,
        attribute_type='CATEGORY'
    ).count()

    handle_webhook_callback(body, workspace.id)

    final_count = ExpenseAttribute.objects.filter(
        workspace_id=workspace.id,
        attribute_type='CATEGORY'
    ).count()

    assert final_count > initial_count

    expense_attr = ExpenseAttribute.objects.filter(
        workspace_id=workspace.id,
        attribute_type='CATEGORY',
        source_id='12345'
    ).first()

    assert expense_attr is not None
    assert expense_attr.active is True


def test_handle_webhook_callback_attribute_updated_enabled(db):
    workspace = Workspace.objects.get(id=1)

    ExpenseAttribute.objects.create(
        workspace_id=workspace.id,
        attribute_type='PROJECT',
        source_id='67890',
        value='Old Project',
        active=True
    )

    feature_config = FeatureConfig.objects.get(workspace_id=workspace.id)
    feature_config.fyle_webhook_sync_enabled = True
    feature_config.save()

    body = data['webhook_attribute_data']['project_updated'].copy()
    body['data'] = body['data'].copy()
    body['data']['org_id'] = workspace.fyle_org_id

    handle_webhook_callback(body, workspace.id)

    expense_attr = ExpenseAttribute.objects.filter(
        workspace_id=workspace.id,
        attribute_type='PROJECT',
        source_id='67890'
    ).order_by('-updated_at').first()

    assert expense_attr is not None
    assert 'Project Alpha' in expense_attr.value


def test_handle_webhook_callback_attribute_deleted_enabled(db):
    workspace = Workspace.objects.get(id=1)

    ExpenseAttribute.objects.create(
        workspace_id=workspace.id,
        attribute_type='EMPLOYEE',
        source_id='111222',
        value='employee@fyle.in',
        active=True
    )

    feature_config = FeatureConfig.objects.get(workspace_id=workspace.id)
    feature_config.fyle_webhook_sync_enabled = True
    feature_config.save()

    body = data['webhook_attribute_data']['employee_deleted'].copy()
    body['data'] = body['data'].copy()
    body['data']['org_id'] = workspace.fyle_org_id

    handle_webhook_callback(body, workspace.id)

    expense_attr = ExpenseAttribute.objects.get(
        workspace_id=workspace.id,
        source_id='111222'
    )

    assert expense_attr.active is False


def test_handle_webhook_callback_attribute_exception_handling(db):
    workspace = Workspace.objects.get(id=1)

    feature_config = FeatureConfig.objects.get(workspace_id=workspace.id)
    feature_config.fyle_webhook_sync_enabled = True
    feature_config.save()

    body = {
        'action': 'CREATED',
        'resource': 'INVALID_RESOURCE',
        'data': {
            'id': 'invalid_123',
            'org_id': workspace.fyle_org_id
        }
    }

    handle_webhook_callback(body, workspace.id)
