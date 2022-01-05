from logging import FATAL
from apps.workspaces.models import WorkspaceSchedule
import pytest
import json

from apps.workspaces.tasks import run_sync_schedule, schedule_sync

@pytest.mark.django_db(databases=['default'])
def test_schedule_sync():
    schedule_sync(2, True,3)

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.interval_hours == 3
    assert ws_schedule.enabled == True
   
    schedule_sync(2, False, 0)

    ws_schedule = WorkspaceSchedule.objects.filter(workspace_id=2).last()
    assert ws_schedule.enabled == False

@pytest.mark.django_db(databases=['default'])
def test_run_sync_schedule(test_connection, add_fyle_credentials, add_netsuite_credentials):
    run_sync_schedule(1)
