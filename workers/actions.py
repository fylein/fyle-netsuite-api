import os
import signal
import logging
from typing import Dict

import django
from django.utils.module_loading import import_string

from workers.helpers import ACTION_METHOD_MAP, WorkerActionEnum

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fyle_netsuite_api.settings")
django.setup()

logger = logging.getLogger(__name__)
logger.level = logging.INFO

TASK_TIMEOUT_SECONDS = 20 * 60  # 20 minutes


def get_timeout_handler(action: str):
    """
    Create a timeout handler with the action name
    :param action: str - the action/task name
    :return: signal handler function
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(f'Task {action} timed out after 20 minutes')
    return timeout_handler


def handle_tasks(payload: Dict) -> None:
    """
    Handle tasks
    :param data: Dict
    :return: None
    """
    action = payload.get('action')
    data = payload.get('data') or {}

    if action is None:
        logger.error('Action is None for workspace_id - %s', payload.get('workspace_id'))
        return

    try:
        action_enum = WorkerActionEnum(action)
    except ValueError:
        logger.error('Unknown action - %s for workspace_id - %s', action, payload.get('workspace_id'))
        return

    method = ACTION_METHOD_MAP.get(action_enum)

    if method is None:
        logger.error('Method is None for action - %s and workspace_id - %s', action, payload.get('workspace_id'))
        return

    is_import_action = action.startswith('IMPORT.')

    if is_import_action:
        timeout_handler = get_timeout_handler(action)
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TASK_TIMEOUT_SECONDS)

    try:
        import_string(method)(**data)
    finally:
        if is_import_action:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)

