import pytest
import json
from django.urls import reverse

from apps.mappings.models import GeneralMapping, SubsidiaryMapping
from .fixtures import data

@pytest.mark.django_db(databases=['default'])
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

    assert response['internal_id']=='3'
    assert response['subsidiary_name']=='Honeycomb Holdings Inc.'

    SubsidiaryMapping.objects.get(workspace_id=1).delete()

    response = api_client.get(url)

    assert response.status_code == 400
    assert response.data['message'] == 'Subsidiary mappings do not exist for the workspace'


@pytest.mark.django_db(databases=['default'])
def test_post_country_view(api_client, test_connection, add_netsuite_credentials):
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
    assert response['subsidiary_name']=='Honeycomb Holdings Inc.'

    SubsidiaryMapping.objects.get(workspace_id=1).delete()

    response = api_client.post(url)

    assert response.status_code == 400
    assert response.data['message'] == 'Subsidiary mappings do not exist for the workspace'

@pytest.mark.django_db(databases=['default'])
def test_get_general_mappings(api_client, test_connection):
    '''
    Test get of general mappings
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
    assert response['use_employee_department'] == False
    assert response['default_ccc_vendor_name'] == 'Ashwin Vendor'

    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    general_mapping.default_ccc_vendor_name = ''
    general_mapping.use_employee_department = True
    general_mapping.save()
    response = api_client.get(url)

    GeneralMapping.objects.get(workspace_id=1).delete()

    response = api_client.get(url)

    assert response.status_code == 400
    assert response.data['message'] == 'General mappings do not exist for the workspace'

@pytest.mark.django_db(databases=['default'])
def test_post_general_mappings(api_client, test_connection):
    '''
    Test Post of general mappings
    '''
    url = reverse('general-mappings', 
        kwargs={
                'workspace_id': 1
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.post(
        url,
        data=data['general_mapping_payload']
    )

    assert response.status_code == 201
    response = json.loads(response.content)
    assert response['use_employee_department'] == True
    assert response['use_employee_class'] == True


def test_auto_map_employee_trigger(api_client, test_connection):

    url = reverse('auto-map-employees-trigger', 
        kwargs={
                'workspace_id': 2
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.post(url)

    assert response.status_code == 200