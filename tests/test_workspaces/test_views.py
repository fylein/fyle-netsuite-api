import pytest
import json
from django.urls import reverse


from tests.helper import dict_compare_keys, get_response_dict

@pytest.mark.django_db(databases=['default'])
def test_get_workspace_by_id(api_client, test_connection):

    url = reverse(
        'workspace-by-id', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.get(url)
    assert response.status_code == 200

    response = json.loads(response.content)

    expected_response = get_response_dict('test_workspaces/data.json')

    assert dict_compare_keys(response, expected_response['workspace']) == [], 'workspaces api returns a diff in the keys'


@pytest.mark.django_db(databases=['default'])
def test_post_of_workspace(api_client, test_connection):

    url = reverse(
        'workspace'
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.post(url)
    assert response.status_code == 200

    response = json.loads(response.content)

    expected_response = get_response_dict('test_workspaces/data.json')

    assert dict_compare_keys(response, expected_response['workspace']) == [], 'workspaces api returns a diff in the keys'


@pytest.mark.django_db(databases=['default'])
def test_get_configuration_detail(api_client, test_connection):

    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.get(url)
    assert response.status_code == 200
    response = json.loads(response.content)

    expected_response = get_response_dict('test_workspaces/data.json')

    assert dict_compare_keys(response, expected_response['configuration']) == [], 'configuration api returns a diff in keys'
