import json
import pytest
from apps.workspaces.models import Workspace, Configuration
from apps.workspaces.apis.import_settings.triggers import ImportSettingsTrigger
from tests.helper import dict_compare_keys
from tests.test_workspaces.test_apis.test_import_settings.fixtures import data

from django.urls import reverse


@pytest.mark.django_db(databases=['default'])
def test_post_save_configurations_disable_items(mocker):
    mock_publish = mocker.patch('apps.workspaces.apis.import_settings.triggers.publish_to_rabbitmq')
    workspace_id = 1

    old_configuration = Configuration.objects.get(workspace_id=workspace_id)
    old_configuration.import_items = True
    old_configuration.save()

    new_configuration = Configuration.objects.get(workspace_id=workspace_id)
    new_configuration.import_items = False
    new_configuration.save()

    trigger = ImportSettingsTrigger(configurations={}, mapping_settings=[], workspace_id=workspace_id)
    trigger.post_save_configurations(new_configuration, old_configuration)

    mock_publish.assert_called_once()
    call_args = mock_publish.call_args
    assert call_args[1]['payload']['action'] == 'IMPORT.DISABLE_ITEMS'
    assert call_args[1]['payload']['data']['workspace_id'] == workspace_id
    assert call_args[1]['payload']['data']['is_import_enabled'] is False


@pytest.mark.django_db(databases=['default'])
def test_import_settings(mocker, api_client, access_token):
    mocker.patch('fyle_integrations_platform_connector.apis.ExpenseCustomFields.get_by_id', return_value={'options': ['samp'], 'updated_at': '2020-06-11T13:14:55.201598+00:00'})
    mocker.patch('fyle_integrations_platform_connector.apis.ExpenseCustomFields.post', return_value=None)
    mocker.patch('fyle_integrations_platform_connector.apis.ExpenseCustomFields.sync', return_value=None)
    workspace = Workspace.objects.get(id=1)
    workspace.onboarding_state = 'IMPORT_SETTINGS'
    workspace.save()

    url = reverse(
        'import-settings', kwargs={
            'workspace_id': 1
        }
    )
 
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.put(url, data=data['import_settings'], format='json')

    assert response.status_code == 200

    response = json.loads(response.content)
    assert dict_compare_keys(response, data['response']) == [], 'workspaces api returns a diff in the keys'

    response = api_client.put(url, data=data['import_settings_without_mapping'], format='json')
    assert response.status_code == 200

    invalid_configurations_settings = data['import_settings']
    invalid_configurations_settings['configuration'] = {}
    response = api_client.put(url, data=invalid_configurations_settings, format='json')
    assert response.status_code == 400

    response = api_client.put(url, data=data['invalid_mapping_settings'], format='json')
    assert response.status_code == 400
