from datetime import datetime, timezone
import json
from unittest.mock import ANY, MagicMock
from apps.netsuite.actions import update_last_export_details
from apps.tasks.models import TaskLog
from apps.workspaces.models import LastExportDetail
from .fixtures import data

def test_update_last_export_details(mocker, db):
    """
    `update_last_export_details` when called with failed task logs
    should do a patch request to integrations settings api to 
    update the `errors_count`
    """

    workspace_id = 1
    mocked_patch = MagicMock()
    mocker.patch('apps.fyle.helpers.requests.patch', side_effect=mocked_patch)

    mock_task_logs = data['task_logs']

    for task_log in mock_task_logs:
        TaskLog.objects.create(workspace_id=workspace_id, type=task_log['type'], status=task_log['status'])

    update_last_export_details(workspace_id)

    failed_count = len([i for i in mock_task_logs if i['status'] in ('FAILED', 'FATAL')])
    expected_payload = {'errors_count': failed_count, 'tpa_name': 'Fyle Netsuite Integration'}

    _, kwargs =  mocked_patch.call_args
    actual_payload = json.loads(kwargs['data'])

    assert actual_payload == expected_payload
