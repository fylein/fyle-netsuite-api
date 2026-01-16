import os
import logging
from typing import Dict

import django
from django.utils.module_loading import import_string

from workers.helpers import ACTION_METHOD_MAP

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fyle_netsuite_api.settings")
django.setup()

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def handle_tasks(payload: Dict) -> None:
    """
    Handle tasks
    :param data: Dict
    :return: None
    """
    action = payload.get('action')
    data = payload.get('data')

    if action is None:
        logger.error('Action is None for payload - %s', data)
        return

    method = ACTION_METHOD_MAP.get(action)

    if method is None:
        logger.error('Method is None for action - %s and payload - %s', action, data)
        return

    import_string(method)(**data)

