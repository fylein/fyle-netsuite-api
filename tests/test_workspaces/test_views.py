import pytest
import json
from unittest import mock
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from django.core.cache import cache

from fyle_netsuite_api.tests import settings
from django.urls import reverse
from django.db.models import Q
from apps.tasks.models import TaskLog
from apps.workspaces.models import Configuration, FyleCredential, NetSuiteCredentials, WorkspaceSchedule, LastExportDetail, Workspace
from .fixtures import *
from fyle_accounting_mappings.models import ExpenseAttribute
from tests.test_netsuite.fixtures import data as netsuite_data
from tests.test_fyle.fixtures import data as fyle_data
from tests.helper import dict_compare_keys, get_response_dict
from fyle.platform import exceptions as fyle_exc


@pytest.mark.django_db(databases=['default'])
def test_token_health_view(api_client, access_token, mocker):
    workspace_id = 1

    url = f"/api/workspaces/{workspace_id}/token_health/"
    api_client.credentials(HTTP_AUTHORIZATION="Bearer {}".format(access_token))

    # Clean cache before test
    cache_key = f'HEALTH_CHECK_CACHE_{workspace_id}'
    cache.delete(cache_key)

    NetSuiteCredentials.objects.filter(workspace=workspace_id).delete()
    response = api_client.get(url)

    assert response.status_code == 400
    assert response.data["message"] == "Netsuite credentials not found"

    workspace = Workspace.objects.get(id=workspace_id)
    NetSuiteCredentials.objects.all().delete()
    NetSuiteCredentials.objects.create(workspace=workspace, is_expired=True)
    response = api_client.get(url)

    assert response.status_code == 400
    assert response.data["message"] == "Netsuite connection expired"

    NetSuiteCredentials.objects.all().delete()
    NetSuiteCredentials.objects.create(workspace=workspace, is_expired=False)

    mock_connector = mocker.patch('apps.workspaces.views.NetSuiteConnector')
    mock_instance = MagicMock()
    mock_connector.return_value = mock_instance
    mock_instance.connection.locations.count.side_effect = Exception("Invalid")
    
    # Mocking invalidate function
    mocker.patch('apps.workspaces.views.invalidate_netsuite_credentials', return_value=None)

    response = api_client.get(url)
    
    assert response.status_code == 400
    assert response.data["message"] == "Netsuite connection expired"
    
    # Reseting mocks for successful connection test
    mocker.resetall()
    mock_connector = mocker.patch('apps.workspaces.views.NetSuiteConnector')
    mock_instance = MagicMock()
    mock_connector.return_value = mock_instance
    mock_instance.connection.locations.count.return_value = 1
    
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data["message"] == "Netsuite connection is active"
    
    cache.set(cache_key, True, timeout=timedelta(hours=24).total_seconds())

    # Assert cache is present and true
    assert cache.get(cache_key) == True
    
    mock_connector.reset_mock()
    response = api_client.get(url)
    
    assert response.status_code == 200
    assert response.data["message"] == "Netsuite connection is active"
    mock_connector.assert_not_called()


@pytest.mark.django_db(databases=['default'])
def test_get_workspace(api_client, access_token):

    url = reverse('workspace')

    api_client.get(url, {
        'org_id': 'orf6t6jWUnpx'
    })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    assert response.status_code == 200

    response = json.loads(response.content)
    expected_response = get_response_dict('test_workspaces/data.json')
    assert dict_compare_keys(response, expected_response['workspace']) == [], 'workspaces api returns a diff in the keys'


@pytest.mark.django_db(databases=['default'])
def test_get_workspace_by_id(api_client, access_token):

    url = reverse(
        'workspace-by-id', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
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
def test_post_of_workspace(api_client, access_token, mocker):

    url = reverse(
        'workspace'
    )

    mocker.patch(
        'apps.workspaces.views.get_fyle_admin',
        return_value=fyle_data['get_my_profile']
    )

    mocker.patch(
        'apps.workspaces.views.get_cluster_domain',
        return_value={
            'cluster_domain': 'https://staging.fyle.tech/'
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.post(url)
    assert response.status_code == 200

    response = json.loads(response.content)
    expected_response = get_response_dict('test_workspaces/data.json')
    
    assert dict_compare_keys(response, expected_response['workspace']) == [], 'workspaces api returns a diff in the keys'

    mocker.patch(
        'apps.workspaces.views.get_fyle_admin',
        return_value={'data': {'org': {'name': 'Fyle For Arkham Asylum', 'id': 'or79Cob97KSh', 'currency': 'USD'}}}
    )
    response = api_client.post(url)
    assert response.status_code == 200


@pytest.mark.django_db(databases=['default'])
def test_get_configuration_detail(api_client, access_token):

    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.get(url)
    assert response.status_code == 200
    response = json.loads(response.content)

    expected_response = get_response_dict('test_workspaces/data.json')

    assert dict_compare_keys(response, expected_response['configuration']) == [], 'configuration api returns a diff in keys'


def test_post_netsuite_credentials(api_client, access_token, mocker, db):
    mocker.patch(
        'netsuitesdk.api.accounts.Accounts.get_all_generator',
        return_value=netsuite_data['get_all_accounts']    
    )

    url = reverse(
        'post-netsuite-credentials', kwargs={
            'workspace_id': 1
        }
    )
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    paylaod = create_netsuite_credential_object_payload(1)

    response = api_client.post(
        url,
        data=paylaod
    )
    assert response.status_code == 200

    netsuite_credentials = NetSuiteCredentials.objects.filter(workspace=1).first()
    netsuite_credentials.ns_account_id = 'sdfghjk'
    netsuite_credentials.save()

    response = api_client.post(
        url,
        data=paylaod
    )
    assert response.status_code == 400

    netsuite_credentials = NetSuiteCredentials.objects.filter(workspace=1).first()
    netsuite_credentials.delete()

    paylaod = create_netsuite_credential_object_payload(1)
    response = api_client.post(
        url,
        data=paylaod
    )
    assert response.status_code == 200
    
 
@pytest.mark.django_db(databases=['default'])
def test_post_workspace_configurations(api_client, access_token):
    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

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
def test_get_workspace_configuration(api_client, access_token):
    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    response = json.loads(response.content)

    expected_response = get_response_dict('test_workspaces/data.json')

    assert dict_compare_keys(response, expected_response['configuration']) == [], 'configuration api returns a diff in keys'

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.delete()

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.get(url)
    response = json.loads(response.content)

    assert response == {'message': 'General Settings does not exist in workspace'}


@pytest.mark.django_db(databases=['default'])
def test_patch_workspace_configuration(api_client, access_token):

    url = reverse(
        'workspace-configurations', kwargs={
            'workspace_id': 1
        }
    )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    configuration = Configuration.objects.get(workspace_id=1)
    configuration.created_by = 'ashu@gmail.com'
    configuration.updated_by = 'ashu@gmail.com'
    configuration.save()
    configuration.auto_create_destination_entity = True
    configuration.auto_map_employees = ''

    response = api_client.patch(
        url,
        data=configuration.__dict__
    )

    response = json.loads(response.content)
    assert response['auto_create_destination_entity'] == True

@pytest.mark.django_db(databases=['default'])
def test_ready_view(api_client, access_token):
    url = reverse('ready')

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    response = json.loads(response.content)

    assert response == {'message': 'Ready'}

@pytest.mark.django_db(databases=['default'])
def test_get_fyle_credentials(api_client, access_token, add_fyle_credentials):
    url = reverse('get-fyle-credentials', kwargs={
            'workspace_id': 1
        })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.get(url)

    response = json.loads(response.content)
    assert response['refresh_token'] == settings.FYLE_REFRESH_TOKEN

    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    fyle_credentials.delete()

    response = api_client.get(url)

    response = json.loads(response.content)
    assert response['message'] == 'Fyle Credentials not found in this workspace'

@pytest.mark.django_db(databases=['default'])
def test_delete_fyle_credentials(api_client, access_token, add_fyle_credentials):
    url = reverse('delete-fyle-credentials', kwargs={
        'workspace_id': 1
    })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.delete(url)

    response = json.loads(response.content)
    assert response['message'] == 'Fyle credentials deleted'


def test_post_connect_fyle_view(mocker, api_client, access_token):
    mocker.patch(
        'fyle_rest_auth.utils.AuthUtils.generate_fyle_refresh_token',
        return_value={'refresh_token': 'asdfghjk', 'access_token': 'qwertyuio'}
    )
    mocker.patch(
        'apps.workspaces.views.get_fyle_admin',
        return_value={'data': {'org': {'name': 'Fyle For Arkham Asylum', 'id': 'or79Cob97KSh', 'currency': 'USD'}}}
    )
    mocker.patch(
        'apps.workspaces.views.get_cluster_domain',
        return_value='https://staging.fyle.tech'
    )
    code = 'asd'
    url = '/api/workspaces/1/connect_fyle/authorization_code/'

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.post(
        url,
        data={'code': code}    
    )
    response = api_client.post(url)
    assert response.status_code == 200


def test_connect_fyle_view_exceptions(api_client, access_token):
    workspace_id = 1
    
    code = 'qwertyu'
    url = '/api/workspaces/{}/connect_fyle/authorization_code/'.format(workspace_id)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    
    with mock.patch('fyle_rest_auth.utils.AuthUtils.generate_fyle_refresh_token') as mock_call:
        mock_call.side_effect = fyle_exc.UnauthorizedClientError(msg='Invalid Authorization Code', response='Invalid Authorization Code')
        
        response = api_client.post(
            url,
            data={'code': code}    
        )
        assert response.status_code == 403

        mock_call.side_effect = fyle_exc.NotFoundClientError(msg='Fyle Application not found', response='Fyle Application not found')
        
        response = api_client.post(
            url,
            data={'code': code}    
        )
        assert response.status_code == 404

        mock_call.side_effect = fyle_exc.WrongParamsError(msg='Some of the parameters are wrong', response='Some of the parameters are wrong')
        
        response = api_client.post(
            url,
            data={'code': code}    
        )
        assert response.status_code == 400

        mock_call.side_effect = fyle_exc.InternalServerError(msg='Wrong/Expired Authorization code', response='Wrong/Expired Authorization code')
        
        response = api_client.post(
            url,
            data={'code': code}    
        )
        assert response.status_code == 401

        mock_call.side_effect = Exception()
        
        response = api_client.post(
            url,
            data={'code': code}    
        )
        assert response.status_code == 403


@pytest.mark.django_db(databases=['default'])
def test_get_and_delete_netsuite_crendentials(api_client, access_token, add_netsuite_credentials):
    url = reverse('get-netsuite-credentials', kwargs={
        'workspace_id': 1
    })

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    netsuite_credentials = NetSuiteCredentials.objects.filter(workspace=1).first()
    netsuite_credentials.ns_account_id = settings.NS_ACCOUNT_ID
    netsuite_credentials.save()

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
def test_get_workspace_admin_view(api_client, access_token, db):
    url = reverse(
        'admin', kwargs={
            'workspace_id': 1
        }
    )
    name = ExpenseAttribute.objects.get(id=1)
    name.value = 'admin1@fylefornt.com'
    name.save()

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.get(url)
    assert response.status_code == 200
    response = json.loads(response.content)

    assert response[0]['email'] == 'ashwin.t@fyle.in'

@pytest.mark.django_db(databases=['default'])
def test_export_to_netsuite(mocker, api_client, access_token):
    mocker.patch(
        'apps.workspaces.views.export_to_netsuite',
        return_value=None
    )

    workspace_id = 1
    url = '/api/workspaces/{}/exports/trigger/'.format(workspace_id)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.post(url)
    assert response.status_code == 200


@pytest.mark.django_db(databases=['default'])
def test_last_export_detail_view(api_client, access_token):

    workspace_id = 1
    LastExportDetail.objects.create(workspace_id=1, export_mode='MANUAL', total_expense_groups_count=2, 
                successful_expense_groups_count=0, failed_expense_groups_count=0, last_exported_at='2023-07-07 11:57:53.184441+00', 
                created_at='2023-07-07 11:57:53.184441+00', updated_at='2023-07-07 11:57:53.184441+00')

    url = '/api/workspaces/{}/export_detail/'.format(workspace_id)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)

    assert response.status_code == 200

    last_export_detail = LastExportDetail.objects.filter(workspace_id=workspace_id).first()
    last_export_detail.total_expense_groups_count = 0
    last_export_detail.save()

    response = api_client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db(databases=['default'])
def test_last_export_detail_2(mocker, api_client, access_token):
    workspace_id = 1

    Configuration.objects.filter(workspace_id=workspace_id).update(
        reimbursable_expenses_object='BILL',
        corporate_credit_card_expenses_object='BILL'
    )

    url = "/api/workspaces/{}/export_detail/?start_date=2025-05-01".format(workspace_id)

    api_client.credentials(
        HTTP_AUTHORIZATION="Bearer {}".format(access_token)
    )

    LastExportDetail.objects.create(workspace_id=workspace_id, last_exported_at=datetime.now(), total_expense_groups_count=1)

    TaskLog.objects.create(type='CREATING_EXPENSE_REPORT', status='COMPLETE', workspace_id=workspace_id)

    failed_count = TaskLog.objects.filter(workspace_id=workspace_id, status__in=['FAILED', 'FATAL']).count()

    response = api_client.get(url)
    assert response.status_code == 200

    response = json.loads(response.content)
    assert response['repurposed_successful_count'] == 1
    assert response['repurposed_failed_count'] == failed_count
    assert response['repurposed_last_exported_at'] is not None
