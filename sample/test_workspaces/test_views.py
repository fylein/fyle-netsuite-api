import pytest
import json
from django.http import response
from fyle_netsuite_api.tests import settings
from django.urls import reverse
from apps.workspaces.models import Configuration, FyleCredential, NetSuiteCredentials, Workspace, WorkspaceSchedule
from tests.conftest import api_client
from fyle_rest_auth.models import AuthToken, User
from .fixtures import create_netsuite_credential_object_payload, create_configurations_object_payload, \
    create_workspace


from tests.helper import dict_compare_keys, get_response_dict


@pytest.mark.django_db(databases=['default'])
def test_get_workspace(api_client, test_connection):

    url = reverse('workspace')

    api_client.get(url, {
        'org_id': 'orf6t6jWUnpx'
    })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.get(url)
    assert response.status_code == 200

    response = json.loads(response.content)
    expected_response = get_response_dict('test_workspaces/data.json')
    assert dict_compare_keys(response, expected_response['workspace']) == [], 'workspaces api returns a diff in the keys'

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

    
    url = reverse(
            'workspace-by-id', kwargs={
                'workspace_id': 5
            }
        )

    response = api_client.get(url)
    assert response.status_code == 400
    response = json.loads(response.content)

    assert response['message'] == 'Workspace with this id does not exist'


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

@pytest.mark.django_db(databases=['default'])
def test_post_netsuite_credentials(api_client, test_connection):

    url = reverse(
        'post-netsuite-credentials', kwargs={
            'workspace_id': 1
        }
    )
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    paylaod = create_netsuite_credential_object_payload(1)
    response = api_client.post(
        url,
        data=paylaod
    )
    assert response.status_code==200
 
@pytest.mark.django_db(databases=['default'])
def test_post_workspace_configurations(api_client, test_connection):
    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.post(
        url,
        data=create_configurations_object_payload(1)
    )

    assert response.status_code==201

@pytest.mark.django_db(databases=['default'])
def test_get_workspace_configuration(api_client, test_connection):
    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.get(url)
    response = json.loads(response.content)

    expected_response = get_response_dict('test_workspaces/data.json')

    assert dict_compare_keys(response, expected_response['configuration']) == [], 'configuration api returns a diff in keys'

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.delete()

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.get(url)
    response = json.loads(response.content)

    assert response == {'message': 'General Settings does not exist in workspace'}

def test_post_workspace_schedule(api_client, test_connection):
    url = reverse(
         'workspace-schedule', kwargs={
            'workspace_id': 1
        }
    )
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.post(url, {
        'schedule_enabled': False,
        'hours': 0
    })
    assert response.status_code == 200

def test_get_workspace_schedule(api_client, test_connection):
    url = reverse(
        'workspace-schedule', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.get(url)
    response = json.loads(response.content)

    assert response['message'] == 'Schedule settings does not exist in workspace'

    WorkspaceSchedule.objects.get_or_create(
        workspace_id=1
    )

    response = api_client.get(url)
    response = json.loads(response.content)
    expected_response = get_response_dict('test_workspaces/data.json')

    assert dict_compare_keys(response, expected_response['workspace_schedule']) == [] , 'workspace-schedule api returns a diff in keys'

@pytest.mark.django_db(databases=['default'])
def test_ready_view(api_client, test_connection):
    url = reverse('ready')

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))

    response = api_client.get(url)
    response = json.loads(response.content)

    assert response == {'message': 'Ready'}

@pytest.mark.django_db(databases=['default'])
def test_get_fyle_credentials(api_client, test_connection, add_fyle_credentials):
    url = reverse('get-fyle-credentials', kwargs={
            'workspace_id': 1
        })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.get(url)

    response = json.loads(response.content)
    assert response['refresh_token'] == settings.FYLE_REFRESH_TOKEN

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = api_client.get(url)

    response = json.loads(response.content)
    assert response['message'] == 'Fyle Credentials not found in this workspace'

@pytest.mark.django_db(databases=['default'])
def test_delete_fyle_credentials(api_client, test_connection, add_fyle_credentials):
    url = reverse('delete-fyle-credentials', kwargs={
        'workspace_id': 1
    })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.delete(url)

    response = json.loads(response.content)
    assert response['message'] == 'Fyle credentials deleted'

@pytest.mark.django_db(databases=['default'])
def test_get_and_delete_netsuite_crendentials(api_client, test_connection, add_netsuite_credentials):
    url = reverse('get-netsuite-credentials', kwargs={
        'workspace_id': 1
    })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.get(url)

    response = json.loads(response.content)
    assert response['ns_account_id'] == settings.NS_ACCOUNT_ID

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    netsuite_credentials.delete()

    response = api_client.get(url)

    response = json.loads(response.content)
    assert response['message'] == 'NetSuite Credentials not found in this workspace'

    url = reverse('delete-netsuite-credentials', kwargs={
        'workspace_id': 1
    })

    response = api_client.delete(url)
    response = json.loads(response.content)

    assert response['message'] == 'NetSuite credentials deleted'