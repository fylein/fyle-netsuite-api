from time import sleep
import pytest
from django_q.models import Schedule

from apps.mappings.helpers import validate_and_trigger_auto_map_employees


def test_validate_and_trigger_auto_map_employees(db):
    validate_and_trigger_auto_map_employees(workspace_id=2)
