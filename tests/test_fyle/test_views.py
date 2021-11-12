import pytest
import json

from django.urls import reverse
from apps.fyle.models import ExpenseGroup
from tests.helper import dict_compare_keys

from .fixtures import data

#  Will use paramaterize decorator of python later
@pytest.mark.django_db(databases=['default'])
@pytest.mark.skip
def test_fyle_fields_view(api_client, test_connection, sync_fyle_dimensions):
    
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

   assert response[2]['attribute_type'] == 'FYLE_TEST_FIELD'
   assert len(response) == 3

@pytest.mark.django_db(databases=['default'])
def test_expense_group_id_view(api_client, test_connection, create_expense_group):
    
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
def test_expense_view(api_client, test_connection, create_expense_group):
    
   access_token = test_connection.access_token

   expense_group = ExpenseGroup.objects.filter(workspace_id=1).first()
   url = reverse('expense-group-expenses', 
      kwargs={
            'workspace_id': 1,
            'expense_group_id': expense_group.id
         }
      )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['expense_group_expenses']) == [], 'expenses group expenses returns diffs in keys'
