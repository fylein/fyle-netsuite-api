import pytest
import json
from django.urls import reverse

from apps.mappings.models import GeneralMapping, SubsidiaryMapping
from apps.workspaces.models import Configuration
from .fixtures import data

@pytest.mark.django_db(databases=['default'])
def test_subsidiary_mapping_view(api_client, access_token):
    '''
    Test Post of User Profile
    '''

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
def test_post_country_view(api_client, access_token, add_netsuite_credentials):
    '''
    Test Post of User Profile
    '''
    url = reverse('country', 
        kwargs={
                'workspace_id': 1
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.post(url)
    response = json.loads(response.content)

    assert response['country_name']=='_unitedStates'
    assert response['subsidiary_name']=='Honeycomb Holdings Inc.'

    SubsidiaryMapping.objects.get(workspace_id=1).delete()

    response = api_client.post(url)

    assert response.status_code == 400
    assert response.data['message'] == 'Subsidiary mappings do not exist for the workspace'

@pytest.mark.django_db(databases=['default'])
def test_get_general_mappings(api_client, access_token):
    '''
    Test get of general mappings
    '''
    url = reverse('general-mappings', 
        kwargs={
                'workspace_id': 1
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

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


@pytest.mark.django_db()
def test_post_general_mappings(api_client, access_token, db):
    '''
    Test Post of general mappings
    '''
    url = reverse('general-mappings', 
        kwargs={
                'workspace_id': 1
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.post(
        url,
        data=data['general_mapping_payload']
    )

    assert response.status_code == 201
    response = json.loads(response.content)
    assert response['use_employee_department'] == True
    assert response['use_employee_class'] == True

    invalid_data = data['general_mapping_payload']

    invalid_data['accounts_payable_name'] = ''
    response = api_client.post(
        url,
        data=invalid_data
    )

    assert response.status_code == 400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Accounts payable is missing'

    invalid_data['accounts_payable_name'] = 'Accounts Payable'
    invalid_data['reimbursable_account_name'] = ''

    response = api_client.post(
        url,
        data=invalid_data
    )
    
    assert response.status_code == 400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Reimbursable account is missing'

    invalid_data['reimbursable_account_name'] = 'Unapproved Expense Reports'
    invalid_data['default_ccc_vendor_name'] = ''

    response = api_client.post(
        url,
        data=invalid_data
    )
    
    assert response.status_code == 400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Default CCC vendor is missing'

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.corporate_credit_card_expenses_object = 'CREDIT CARD CHARGE'
    configuration.save()

    invalid_data['default_ccc_vendor_name'] = 'Ashwin Vendor'
    invalid_data['default_ccc_account_name'] = ''
    
    response = api_client.post(
        url,
        data=invalid_data
    )
    
    assert response.status_code == 400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Default CCC account is missing'

    invalid_data['default_ccc_account_name'] = 'sample'
    invalid_data['default_ccc_account_id'] = '12'

    configuration.sync_fyle_to_netsuite_payments = True
    configuration.save()

    response = api_client.post(
        url,
        data=invalid_data
    )
    
    assert response.status_code == 400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'Vendor payment account is missing'

    configuration.sync_fyle_to_netsuite_payments = False
    configuration.save()

    invalid_data['default_ccc_account_name'] = 'sample'
    invalid_data['default_ccc_account_id'] = '12'
    invalid_data['department_level'] = ''
    
    response = api_client.post(
        url,
        data=invalid_data
    )
    
    assert response.status_code == 400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'department_level cannot be null'

    configuration.employee_field_mapping = 'VENDOR'
    configuration.save()
    
    response = api_client.post(
        url,
        data=invalid_data
    )
    assert response.status_code == 400
    response = json.loads(response.content)
    assert response['non_field_errors'][0] == 'use_employee_department or use_employee_location or use_employee_class can be used only when employee is mapped to employee'


def test_auto_map_employee_trigger(api_client, access_token):

    url = reverse('auto-map-employees-trigger', 
        kwargs={
                'workspace_id': 2
            }
        )

    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.post(url)

    assert response.status_code == 200
    