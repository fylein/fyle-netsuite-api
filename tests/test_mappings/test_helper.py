from time import sleep
import pytest
from django_q.models import Schedule

from apps.mappings.helpers import validate_and_trigger_auto_map_employees
from apps.workspaces.models import Configuration


def test_validate_and_trigger_auto_map_employees(db):
    configuration = Configuration.objects.get(workspace_id=2)
    configuration.auto_map_employees = 'NAME'
    configuration.save()
    
    validate_and_trigger_auto_map_employees(workspace_id=2)
    