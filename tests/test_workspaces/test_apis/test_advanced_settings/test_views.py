import json
from tests.helper import dict_compare_keys
from apps.workspaces.models import Workspace, Configuration
from .fixtures import data
import pytest
from django.urls import reverse

@pytest.mark.django_db(databases=['default'])
def test_advanced_settings(api_client, access_token):

    workspace = Workspace.objects.get(id=1)
    workspace.onboarding_state = 'ADVANCED_CONFIGURATION'
    workspace.save()

    url = reverse(
        'advanced-settings', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.put(
        url,
        data=data['advanced_settings'],
        format='json'
    )

    assert response.status_code == 200

    response = json.loads(response.content)
    workspace = Workspace.objects.get(id=1)

    assert dict_compare_keys(response, data['response']) == [], 'workspaces api returns a diff in the keys'
    assert workspace.onboarding_state == 'COMPLETE'

    response = api_client.put(
        url,
        data={
        'general_mappings':{}},
        format='json'
    )

    assert response.status_code == 400

    response = api_client.put(
        url,
        data={
        'configuration':{}},
        format='json'
    )

    assert response.status_code == 400

    response = api_client.put(
        url,
        data={
        'workspace_schedules':{}},
        format='json'
    )

    assert response.status_code == 400
