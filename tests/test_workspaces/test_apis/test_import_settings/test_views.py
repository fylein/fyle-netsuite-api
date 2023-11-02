import json
import pytest
from apps.workspaces.models import Workspace
from tests.helper import dict_compare_keys
from tests.test_workspaces.test_apis.test_import_settings.fixtures import data

from django.urls import reverse

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
