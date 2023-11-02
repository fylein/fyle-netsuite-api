import json
from tests.helper import dict_compare_keys
from apps.workspaces.models import Workspace, Configuration
from .fixtures import data
import pytest
from django.urls import reverse

@pytest.mark.django_db(databases=['default'])
def test_export_settings(api_client, access_token):

    workspace = Workspace.objects.get(id=1)
    workspace.onboarding_state = 'EXPORT_SETTINGS'
    workspace.save()

    url = reverse(
        'export-settings', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.put(
        url,
        data=data['export_settings'],
        format='json'
    )

    assert response.status_code == 200

    response = json.loads(response.content)
    workspace = Workspace.objects.get(id=1)

    assert dict_compare_keys(response, data['response']) == [], 'workspaces api returns a diff in the keys'
    assert workspace.onboarding_state == 'IMPORT_SETTINGS'

    url = '/api/v2/workspaces/1/export_settings/'
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    payload = data['export_settings']
    payload['expense_group_settings']['reimbursable_expense_group_fields'] = []
    payload['expense_group_settings']['corporate_credit_card_expense_group_fields'] = []
    payload['expense_group_settings']['reimbursable_export_date_type'] = ''
    payload['expense_group_settings']['ccc_export_date_type'] = ''

    response = api_client.put(
        url,
        data=payload,
        format='json'
    )

    assert response.status_code == 200

    response = json.loads(response.content)
    workspace = Workspace.objects.get(id=1)

    assert dict_compare_keys(response, data['response']) == [], 'workspaces api returns a diff in the keys'

    invalid_configurations = data['export_settings_missing_values_configurations']
    response = api_client.put(
        url,
        data=invalid_configurations,
        format='json'
    )

    assert response.status_code == 400

    invalid_expense_group_settings = data['export_settings_missing_values_expense_group_settings']
    response = api_client.put(
        url,
        data=invalid_expense_group_settings,
        format='json'
    )

    assert response.status_code == 400

    invalid_general_mappings = data['export_settings_missing_values_general_mappings']
    response = api_client.put(
        url,
        data=invalid_general_mappings,
        format='json'
    )

    assert response.status_code == 400
