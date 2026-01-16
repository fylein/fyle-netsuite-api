import pytest
from unittest.mock import Mock, patch

from workers.worker import Worker, main
from workers.actions import handle_tasks
from fyle_accounting_library.rabbitmq.models import FailedEvent
from common.event import BaseEvent


@pytest.fixture
def mock_qconnector():
    return Mock()


@pytest.fixture
def export_worker(mock_qconnector):
    worker = Worker(
        rabbitmq_url='mock_url',
        rabbitmq_exchange='mock_exchange',
        queue_name='mock_queue',
        binding_keys=['mock.binding.key'],
        qconnector_cls=Mock(return_value=mock_qconnector),
        event_cls=BaseEvent
    )
    worker.qconnector = mock_qconnector
    worker.event_cls = BaseEvent
    return worker


@pytest.mark.django_db
def test_handle_tasks_action_none():
    payload = {'action': None, 'data': {'workspace_id': 1}}
    result = handle_tasks(payload)
    assert result is None


@pytest.mark.django_db
def test_handle_tasks_method_none():
    payload = {'action': 'INVALID_ACTION_THAT_DOES_NOT_EXIST', 'data': {'workspace_id': 1}}
    result = handle_tasks(payload)
    assert result is None


@pytest.mark.django_db
def test_handle_tasks_success():
    with patch('workers.actions.import_string') as mock_import_string:
        mock_func = Mock()
        mock_import_string.return_value = mock_func

        payload = {
            'action': 'EXPORT.P0.DASHBOARD_SYNC',
            'data': {'workspace_id': 1, 'triggered_by': 'DASHBOARD_SYNC'}
        }
        handle_tasks(payload)

        mock_import_string.assert_called_once_with('apps.workspaces.actions.export_to_netsuite')
        mock_func.assert_called_once_with(workspace_id=1, triggered_by='DASHBOARD_SYNC')


@pytest.mark.django_db
def test_process_message_success(export_worker):
    with patch('workers.worker.handle_tasks') as mock_handle_tasks:
        mock_handle_tasks.return_value = None

        routing_key = 'test.routing.key'
        payload_dict = {
            'workspace_id': 123,
            'action': 'test_action',
            'data': {'some': 'data'}
        }
        event = BaseEvent()
        event.from_dict({'new': payload_dict})

        export_worker.process_message(routing_key, event, 1)

        mock_handle_tasks.assert_called_once_with(payload_dict)
        export_worker.qconnector.acknowledge_message.assert_called_once_with(1)


@pytest.mark.django_db
def test_process_message_exception(export_worker):
    with patch('workers.worker.handle_tasks') as mock_handle_tasks:
        mock_handle_tasks.side_effect = Exception('Test error')

        routing_key = 'test.routing.key'
        payload_dict = {
            'workspace_id': 123,
            'action': 'test_action',
            'data': {'some': 'data'}
        }
        event = BaseEvent()
        event.from_dict({'new': payload_dict})

        export_worker.process_message(routing_key, event, 1)

        mock_handle_tasks.assert_called_once_with(payload_dict)


@pytest.mark.django_db
def test_handle_exception(export_worker):
    routing_key = 'test.routing.key'
    payload_dict = {
        'data': {'some': 'data'},
        'workspace_id': 123
    }
    try:
        raise Exception('Test error')
    except Exception as error:
        export_worker.handle_exception(routing_key, payload_dict, error, 1)

    failed_event = FailedEvent.objects.get(
        routing_key=routing_key,
        workspace_id=123
    )
    assert failed_event.payload == payload_dict
    assert 'Test error' in failed_event.error_traceback
    assert 'Exception: Test error' in failed_event.error_traceback


def test_shutdown(export_worker):
    # Test shutdown with signal arguments
    with patch.object(export_worker, 'shutdown', wraps=export_worker.shutdown) as mock_shutdown:
        export_worker.shutdown(_=15, __=None)  # SIGTERM = 15
        mock_shutdown.assert_called_once_with(_=15, __=None)

    with patch.object(export_worker, 'shutdown', wraps=export_worker.shutdown) as mock_shutdown:
        export_worker.shutdown(_=0, __=None)  # Using default values
        mock_shutdown.assert_called_once_with(_=0, __=None)


@patch('workers.worker.signal.signal')
@patch('workers.worker.Worker')
@patch('workers.worker.create_cache_table')
def test_consume(mock_create_cache_table, mock_worker_class, mock_signal):
    mock_worker = Mock()
    mock_worker_class.return_value = mock_worker

    with patch.dict('os.environ', {'RABBITMQ_URL': 'test_url'}):
        from workers.worker import consume
        consume(queue_name='netsuite_export.p0')

    mock_create_cache_table.assert_called_once()
    mock_worker.connect.assert_called_once()
    mock_worker.start_consuming.assert_called_once()
    assert mock_signal.call_count == 2


@patch('workers.worker.consume')
@patch('workers.worker.argparse.ArgumentParser.parse_args')
def test_main(mock_parse_args, mock_consume):
    mock_args = Mock()
    mock_args.queue_name = 'netsuite_export.p0'
    mock_parse_args.return_value = mock_args

    main()

    mock_consume.assert_called_once_with(queue_name='netsuite_export.p0')

