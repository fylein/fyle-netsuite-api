import pytest
import json

from django.urls import reverse
from apps.fyle.models import ExpenseGroup
from apps.workspaces.models import FyleCredential
from tests.helper import dict_compare_keys

from .fixtures import data


@pytest.mark.django_db(databases=['default'])
def test_expense_group_view(api_client, test_connection):
   access_token = test_connection.access_token
   url = reverse('expense-groups', 
         kwargs={
               'workspace_id': 1,
            }
         )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url, {
      'state': 'COMPLETE'
   })
   assert response.status_code==200

   response = json.loads(response.content)
   assert response == {'count': 0, 'next': None, 'previous': None, 'results': []}
   
   response = api_client.get(url, {
      'state': 'READY'
   })
   response = json.loads(response.content)
   assert response == {'count': 1, 'next': None, 'previous': None, 'results': [{'id': 1, 'fund_source': 'PERSONAL', 'description': {'report_id': 'rpuN3bgphxbK', 'fund_source': 'PERSONAL', 'claim_number': 'C/2021/11/R/5', 'employee_email': 'ashwin.t@fyle.in'}, 'response_logs': None, 'created_at': '2021-11-15T10:29:07.618062Z', 'exported_at': None, 'updated_at': '2021-11-15T11:02:55.125634Z', 'workspace': 1, 'expenses': [1]}]}



@pytest.mark.django_db(databases=['default'])
def test_expense_view(api_client, test_connection):
    
   access_token = test_connection.access_token

   expense_group = ExpenseGroup.objects.filter(workspace_id=2).first()
   url = reverse('expense-group-expenses', 
      kwargs={
            'workspace_id': 2,
            'expense_group_id': expense_group.id
         }
      )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['expense_group_expenses']) == [], 'expenses group expenses returns diffs in keys'

   url = reverse('expense-group-expenses', 
      kwargs={
            'workspace_id': 2,
            'expense_group_id': 443
         }
      )

   response = api_client.get(url)
   assert response.status_code == 400
   assert response.data['message'] == 'Expense group not found'

@pytest.mark.django_db(databases=['default'])
def test_count_expense_view(api_client, test_connection):
   access_token = test_connection.access_token

   url = reverse('expense-groups-count', 
      kwargs={
            'workspace_id': 1,
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   response = api_client.get(url)
   response.status=200
   response.data['count'] == 2


@pytest.mark.django_db(databases=['default'])
def test_expense_group_settings(api_client, test_connection):
   access_token = test_connection.access_token

   url = reverse('expense-group-settings', 
      kwargs={
            'workspace_id': 1,
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   response = api_client.get(url)
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['expense_group_setting_payload']) == [], 'expense group api return diffs in keys'
   assert response['reimbursable_expense_group_fields'] == ['employee_email', 'report_id', 'claim_number', 'fund_source']
   assert response['expense_state'] == 'PAYMENT_PROCESSING'
   assert response['reimbursable_export_date_type'] == 'current_date'
   

#  Will use paramaterize decorator of python later
@pytest.mark.django_db(databases=['default'])
def test_fyle_fields_view(api_client, test_connection):
    
   access_token = test_connection.access_token
   url = reverse('fyle-fields', 
      kwargs={
            'workspace_id': 1
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert response[2]['attribute_type'] == 'CLASS'
   assert len(response) == 15


@pytest.mark.django_db(databases=['default'])
def test_fyle_expense_attribute_view(api_client, test_connection):
   access_token = test_connection.access_token
   url = reverse('expense-attributes', 
      kwargs={
            'workspace_id': 2
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url, {
      'attribute_type': 'FYLE_CATEGORY'
   })
   assert response.status_code == 200
   response = json.loads(response.content)
   
   assert response == data['expense_attributes']


@pytest.mark.django_db(databases=['default'])
def test_expense_group_id_view(api_client, test_connection):
    
   access_token = test_connection.access_token

   expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
   url = reverse('expense-group-by-id', 
      kwargs={
            'workspace_id': 1,
            'pk': expense_group.id
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['expense_group_id']) == [], 'expense group api return diffs in keys'


@pytest.mark.django_db(databases=['default'])
def test_fyle_refresh_dimension(api_client, test_connection, add_fyle_credentials):
    
   access_token = test_connection.access_token

   url = reverse('refresh-fyle-dimensions', 
      kwargs={
            'workspace_id': 1,
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)
   assert response.status_code == 200

   fyle_credentials = FyleCredential.objects.get(workspace_id=1)
   fyle_credentials.delete()

   response = api_client.post(url)
   assert response.status_code == 400
   assert response.data['message'] == 'Fyle credentials not found in workspace'

@pytest.mark.django_db(databases=['default'])
def test_fyle_sync_dimension(api_client, test_connection, add_fyle_credentials):
    
   access_token = test_connection.access_token

   url = reverse('sync-fyle-dimensions', 
      kwargs={
            'workspace_id': 1,
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)
   assert response.status_code == 200

   fyle_credentials = FyleCredential.objects.get(workspace_id=1)
   fyle_credentials.delete()

   response = api_client.post(url)
   assert response.status_code == 400
   assert response.data['message'] == 'Fyle credentials not found in workspace'
