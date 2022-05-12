import pytest
import json
from django.http import response
from apps import fyle
from fyle_netsuite_api.tests import settings
from django.urls import reverse
from apps.workspaces.models import Configuration, FyleCredential, NetSuiteCredentials, Workspace, WorkspaceSchedule
from tests.conftest import api_client
from fyle_rest_auth.models import AuthToken, User
from .fixtures import create_netsuite_credential_object_payload, create_configurations_object_payload, \
    create_fyle_credential_object_payload
from fyle_accounting_mappings.models import ExpenseAttribute


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
def test_post_netsuite_credentials(api_client, test_connection, add_netsuite_credentials, add_fyle_credentials):

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

    netsuite_credentials = NetSuiteCredentials.objects.filter(workspace=1).first() 
    netsuite_credentials.delete()

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

    invalid_data = create_configurations_object_payload(1)
    invalid_data['auto_create_destination_entity'] = True
    response = api_client.post(
        url,
        data=invalid_data
    )

    assert response.status_code==400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Cannot set auto_create_destination_entity value if auto map employees is disabled'

    invalid_data['auto_map_employees'] = 'EMPLOYEE_CODE'
    response = api_client.post(
        url,
        data=invalid_data
    )

    assert response.status_code==400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Cannot enable auto create destination entity for employee code'

    invalid_data = create_configurations_object_payload(1)
    invalid_data['corporate_credit_card_expenses_object'] = 'BILL'
    invalid_data['auto_create_merchants'] = True
    response = api_client.post(
        url,
        data=invalid_data
    )

    assert response.status_code==400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Cannot enable auto create merchants without using CC Charge'

    invalid_data = create_configurations_object_payload(1)
    invalid_data['employee_field_mapping'] = 'EMPLOYEE'
    invalid_data['reimbursable_expenses_object'] = 'BILL'
    response = api_client.post(
        url,
        data=invalid_data
    )

    assert response.status_code==400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Reimbursable expenses should be expense report or journal entry for employee mapped to employee'

    invalid_data = create_configurations_object_payload(1)
    invalid_data['employee_field_mapping'] = 'VENDOR'
    invalid_data['reimbursable_expenses_object'] = 'EXPENSE REPORT'
    response = api_client.post(
        url,
        data=invalid_data
    )

    assert response.status_code==400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Reimbursable expenses should be bill or journal entry for employee mapped to vendor'

    invalid_data = create_configurations_object_payload(1)
    invalid_data['corporate_credit_card_expenses_object'] = 'EXPENSE REPORT'
    invalid_data['reimbursable_expenses_object'] = 'BILL'
    response = api_client.post(
        url,
        data=invalid_data
    )

    assert response.status_code==400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Corporate credit card expenses can be expense report if reimbursable expense object is expense report'

    invalid_data = create_configurations_object_payload(1)
    invalid_data['sync_fyle_to_netsuite_payments'] = True
    invalid_data['sync_netsuite_to_fyle_payments'] = True
    invalid_data['reimbursable_expenses_object'] = 'JOURNAL ENTRY'
    response = api_client.post(
        url,
        data=invalid_data
    )

    assert response.status_code==400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Cannot enable sync fyle to netsuite if reimbursable expense object is journal entry'


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


@pytest.mark.django_db(databases=['default'])
def test_patch_workspace_configuration(api_client, test_connection):

    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    configuration = Configuration.objects.get(workspace_id=1)
    configuration.auto_create_destination_entity = True
    configuration.auto_map_employees = ''

    response = api_client.patch(
        url,
        data=configuration.__dict__
    )

    response = json.loads(response.content)
    print(response)
    assert response['auto_create_destination_entity'] == True

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
def test_post_fyle_credentials(api_client, test_connection):
    url = reverse('connect-fyle', kwargs={
            'workspace_id': 1
        })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    paylaod = create_fyle_credential_object_payload(1)
    response = api_client.post(
        url,
        data=paylaod    
    )
    response = api_client.post(url)

    response = json.loads(response.content)
    assert response['message'] == 'Signature has expired'


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

@pytest.mark.django_db(databases=['default'])
def test_get_workspace_admin_view(api_client, test_connection, db):
    url = reverse(
        'admin', kwargs={
            'workspace_id': 1
        }
    )
    name = ExpenseAttribute.objects.get(id=1)
    name.value = 'admin1@fylefornt.com'
    name.save()

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(test_connection.access_token))
    response = api_client.get(url)
    assert response.status_code == 200
    response = json.loads(response.content)

    assert response[0]['email'] == 'admin1@fylefornt.com'
