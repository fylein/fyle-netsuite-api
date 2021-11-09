import pytest
from django.urls import reverse

@pytest.mark.django_db(databases=['cache_db', 'default'])
def test_get_workspace_detail(api_client, test_connection, configuration_with_employee_mapping):

    url = reverse(
        'workspace-by-id', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db(databases=['cache_db', 'default'])
def test_get_workspace_detail(api_client, test_connection, configuration_with_employee_mapping):

    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.get(url)

    assert response.status_code == 200
    
