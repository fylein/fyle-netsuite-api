import pytest
import json
from django.urls import reverse

@pytest.mark.django_db(databases=['cache_db', 'default'])
def test_subsidiary_mapping_view(api_client, test_connection):
    '''
    Test Post of User Profile
    '''
    access_token = test_connection.access_token

    url = reverse('subsidiaries', 
        kwargs={
                'workspace_id': 1
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    response = json.loads(response.content)

    assert response['internal_id']=='1'
    assert response['subsidiary_name']=='Test Subsidiary'

@pytest.mark.django_db(databases=['cache_db', 'default'])
def test_post_country_view(api_client, test_connection):
    '''
    Test Post of User Profile
    '''
    url = reverse('country', 
        kwargs={
                'workspace_id': 1
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.post(url)
    response = json.loads(response.content)

    assert response['country_name']=='_unitedStates'
    assert response['subsidiary_name']=='Test Subsidiary'

@pytest.mark.django_db(databases=['cache_db', 'default'])
def test_general_mappings(api_client, test_connection, create_general_mapping):
    '''
    Test Post of User Profile
    '''
    url = reverse('general-mappings', 
        kwargs={
                'workspace_id': 1
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.get(url)
    assert response.status_code == 200
    response = json.loads(response.content)
    assert response['default_ccc_vendor_name'] == 'Allison Hill'
