from time import sleep
from unittest import mock

import pytest
from django_q.models import Schedule

from apps.mappings.helpers import validate_and_trigger_auto_map_employees, patch_corporate_card_integration_settings
from apps.workspaces.models import Configuration


def test_validate_and_trigger_auto_map_employees(db):
    configuration = Configuration.objects.get(workspace_id=2)
    configuration.auto_map_employees = 'NAME'
    configuration.save()
    
    validate_and_trigger_auto_map_employees(workspace_id=2)


@pytest.mark.django_db()
def test_patch_corporate_card_integration_settings(db):
    """
    Test patch_corporate_card_integration_settings helper - tests all conditions
    """
    workspace_id = 1
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    configuration.corporate_credit_card_expenses_object = 'CREDIT CARD CHARGE'
    configuration.save()

    with mock.patch('apps.mappings.helpers.patch_integration_settings_for_unmapped_cards') as mock_patch:
        patch_corporate_card_integration_settings(workspace_id=workspace_id)
        mock_patch.assert_called_once()
        assert mock_patch.call_args[1]['workspace_id'] == workspace_id
        assert 'unmapped_card_count' in mock_patch.call_args[1]

    # Test that patch is NOT called for non-card expense types
    configuration.corporate_credit_card_expenses_object = 'BILL'
    configuration.save()

    with mock.patch('apps.mappings.helpers.patch_integration_settings_for_unmapped_cards') as mock_patch:
        patch_corporate_card_integration_settings(workspace_id=workspace_id)
        mock_patch.assert_not_called()

    # Test when configuration doesn't exist
    with mock.patch('apps.mappings.helpers.patch_integration_settings_for_unmapped_cards') as mock_patch:
        patch_corporate_card_integration_settings(workspace_id=9999)
        mock_patch.assert_not_called()
    