from asyncio import tasks
import pytest

from apps.tasks.helpers import filter_tasks_by_params

def test_filter_tasks_by_params(db):

    params = {
        "status": "COMPLETE",
        "task_type": "FETCHING_EXPENSES",
    }

    tasks = filter_tasks_by_params(params=params, workspace_id=49)

    assert len(tasks) == 1

    assert tasks[0].id == 141
    assert tasks[0].workspace_id==49

    params = {
        "status": "COMPLETE",
        "task_type": "FETCHING_EXPENSES",
        "expense_group_ids": "1,2"
    }

    tasks = filter_tasks_by_params(params=params, workspace_id=49)
    assert len(tasks) == 0
