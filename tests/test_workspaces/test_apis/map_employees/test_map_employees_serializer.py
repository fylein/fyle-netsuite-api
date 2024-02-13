# test_map_employees_serializer.py

import pytest
from rest_framework.exceptions import ValidationError
from apps.workspaces.models import Workspace, Configuration
from apps.workspaces.apis.map_employees.triggers import MapEmployeesTriggers
from apps.workspaces.apis.map_employees.serializers import MapEmployeesSerializer

@pytest.mark.django_db
def test_map_employees_serializer_update_method(mocker):

    # Create mock data for the update method
    validated_data = {
        'configuration': {
            'employee_field_mapping': 'NAME',
            'auto_map_employees': 'NAME',
        }
    }

    workspace_instance = Workspace.objects.get(id=1)
    workspace_instance.onboarding_state = 'MAP_EMPLOYEES'
    workspace_instance.save()
    configuration_instance = Configuration.objects.get(workspace_id=1)

    # Mock the MapEmployeesTriggers.run_configurations_triggers method
    mocker.patch('apps.workspaces.apis.map_employees.triggers.MapEmployeesTriggers.run_configurations_triggers')

    # Create an instance of MapEmployeesSerializer
    serializer = MapEmployeesSerializer(instance=workspace_instance)

    # Call the update method
    result_instance = serializer.update(workspace_instance, validated_data)

    # Assert that the onboarding_state is updated
    assert result_instance.onboarding_state == 'EXPORT_SETTINGS'


@pytest.mark.django_db
def test_map_employees_serializer_validate_method():
    # Create an instance of MapEmployeesSerializer
    serializer = MapEmployeesSerializer()

    # Test case: Missing employee_field_mapping field
    with pytest.raises(ValidationError, match='employee_field_mapping field is required'):
        serializer.validate({'configuration': {'auto_map_employees': 'EMAIL'}})

    # Test case: Invalid auto_map_employees value
    with pytest.raises(ValidationError, match='auto_map_employees can have only EMAIL / NAME / EMPLOYEE_CODE'):
        serializer.validate({'configuration': {'employee_field_mapping': 'NAME', 'auto_map_employees': 'INVALID_VALUE'}})
