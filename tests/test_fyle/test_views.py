import json
import pytest
from unittest import mock
from django.urls import reverse
from apps.fyle.models import ExpenseGroup
from apps.workspaces.models import FyleCredential, Workspace
from tests.helper import dict_compare_keys
from .fixtures import data


@pytest.mark.django_db(databases=['default'])
def test_expense_group_view(api_client, access_token):

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
   assert response['count'] == 2

   response = api_client.get(url, {
      'state': 'FAILED'
   })

   response = json.loads(response.content)
   assert response == {'count': 0, 'next': None, 'previous': None, 'results': []}

   response = api_client.get(url, {
      'expense_group_ids': '1,2'
    })
   response = response.json()
   assert response['count'] == 2
   

@pytest.mark.django_db(databases=['default'])
def test_expense_view(api_client, access_token):
    
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
def test_count_expense_view(api_client, access_token):

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
def test_expense_group_settings(api_client, access_token):

   url = reverse('expense-group-settings', 
      kwargs={
            'workspace_id': 1,
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   response = api_client.get(url)
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['expense_group_setting_response']) == [], 'expense group api return diffs in keys'
   assert response['reimbursable_expense_group_fields'] == ['employee_email', 'report_id', 'claim_number', 'fund_source']
   assert response['expense_state'] == 'PAYMENT_PROCESSING'
   assert response['ccc_expense_state'] == 'PAID'
   assert response['reimbursable_export_date_type'] == 'current_date'
   
   post_response = api_client.post(
      url,
      data = data['expense_group_setting_payload']
   )
      
   assert post_response.status_code == 200
   post_response = json.loads(post_response.content)

   assert dict_compare_keys(post_response, data['expense_group_setting_response']) == [], 'expense group api return diffs in keys'


#  Will use paramaterize decorator of python later
@pytest.mark.django_db(databases=['default'])
def test_fyle_fields_view(api_client, access_token):
    
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
def test_fyle_expense_attribute_view(api_client, access_token):

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
def test_expense_group_id_view(api_client, access_token):

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
def test_fyle_refresh_dimension(api_client, access_token, mocker):
   mocker.patch(
      'fyle.platform.apis.v1beta.admin.Employees.list_all',
      return_value=data['get_all_employees']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.Categories.list_all',
      return_value=[]
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.Projects.list_all',
      return_value=data['get_all_projects']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.CostCenters.list_all',
      return_value=data['get_all_cost_centers']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.ExpenseFields.list_all',
      return_value=data['get_all_expense_fields']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.CorporateCards.list_all',
      return_value=data['get_all_corporate_cards']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.TaxGroups.list_all',
      return_value=data['get_all_tax_groups']
   )

   url = reverse('refresh-fyle-dimensions',
      kwargs={
         'workspace_id': 1,
      }
   )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)
   assert response.status_code == 200

   with mock.patch('apps.fyle.views.Workspace.objects.get') as mock_call:
      mock_call.side_effect = Exception()

      response = api_client.post(url)
      assert response.status_code == 400
      assert response.data['message'] == 'Error in refreshing Dimensions'

   fyle_credentials = FyleCredential.objects.get(workspace_id=1)
   fyle_credentials.delete()

   response = api_client.post(url)
   assert response.status_code == 400
   assert response.data['message'] == 'Fyle credentials not found in workspace / Invalid Token'


@pytest.mark.django_db(databases=['default'])
def test_fyle_sync_dimension(api_client, access_token, mocker):
   mocker.patch(
      'fyle.platform.apis.v1beta.admin.Employees.list_all',
      return_value=data['get_all_employees']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.Categories.list_all',
      return_value=data['get_all_categories']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.Projects.list_all',
      return_value=data['get_all_projects']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.CostCenters.list_all',
      return_value=data['get_all_cost_centers']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.ExpenseFields.list_all',
      return_value=data['get_all_expense_fields']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.CorporateCards.list_all',
      return_value=data['get_all_corporate_cards']
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.TaxGroups.list_all',
      return_value=data['get_all_tax_groups']
   )

   url = reverse('sync-fyle-dimensions', 
      kwargs={
            'workspace_id': 1,
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)
   assert response.status_code == 200

   with mock.patch('apps.fyle.views.Workspace.objects.get') as mock_call:
      mock_call.side_effect = Exception()

      response = api_client.post(url)
      assert response.status_code == 400
      assert response.data['message'] == 'Error in syncing Dimensions'

   fyle_credentials = FyleCredential.objects.get(workspace_id=1)
   fyle_credentials.delete()

   response = api_client.post(url)
   assert response.status_code == 400
   assert response.data['message'] == 'Fyle credentials not found in workspace / Invalid Token'


def test_expense_group_schedule_view(api_client, access_token):

   url = reverse('expense-groups-trigger', 
      kwargs={
            'workspace_id': 1,
         }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)
   assert response.status_code == 200

@pytest.mark.django_db(databases=['default'])
def test_expense_filters(api_client, access_token):

   url = reverse('expense-filters', 
      kwargs={
         'workspace_id': 1,
      }
   )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   response = api_client.post(url,data=data['expense_filter_1'])
   assert response.status_code == 201
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['expense_filter_1_response']) == [], 'expense group api return diffs in keys'

   response = api_client.post(url,data=data['expense_filter_2'])
   assert response.status_code == 201
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['expense_filter_2_response']) == [], 'expense group api return diffs in keys'

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['expense_filters_response']) == [], 'expense group api return diffs in keys'

   url = reverse('expense-filters-delete',
                 kwargs={
                     'workspace_id': 1,
                     'pk': 2
                 })

   response = api_client.delete(url)
   assert response.status_code == 204


@pytest.mark.django_db(databases=['default'])
def test_custom_fields(mocker, api_client, access_token):

   url = reverse('custom-field', 
      kwargs={
         'workspace_id': 1,
      }
   )

   mocker.patch(
      'fyle.platform.apis.v1beta.admin.expense_fields.list_all',
      return_value=data['get_all_custom_fields']
   )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['custom_fields_response']) == [], 'expense group api return diffs in keys'


@pytest.mark.django_db(databases=['default'])
def test_expenses(mocker, api_client, access_token):

   url = reverse('expenses', 
      kwargs={
         'workspace_id': 1,
      }
   )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert dict_compare_keys(response, data['skipped_expenses']) == [], 'expense group api return diffs in keys'


@pytest.mark.django_db(databases=['default'])
def test_exportable_expense_group_view(api_client, access_token):

   url = '/api/workspaces/1/fyle/exportable_expense_groups/'
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code==200

   response = json.loads(response.content)
   assert response['exportable_expense_group_ids'] == [1, 2]
