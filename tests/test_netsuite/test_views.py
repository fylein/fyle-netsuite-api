from os import access
from django.http import response
import pytest
import json

from django.urls import reverse
from apps.fyle.models import ExpenseGroup
from apps.workspaces.models import NetSuiteCredentials

from .fixtures import data

#  Will use paramaterize decorator of python later
@pytest.mark.django_db(databases=['default'])
def test_netsutie_fields_view(api_client, test_connection):

   access_token = test_connection.access_token
   url = reverse('netsuite-fields', 
      kwargs={
            'workspace_id': 1
         }
      )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert len(response) == 4


@pytest.mark.django_db(databases=['default'])
def test_destination_attribute_view(api_client, test_connection):

   access_token = test_connection.access_token
   url = reverse('destination-attributes',
      kwargs={
         'workspace_id': 1
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url, {
      'attribute_types': 'SUBSIDIARY'
   })

   assert response.status_code == 200
   response = json.loads(response.content)

   assert response[0] == data['destination_attributes'][0]


@pytest.mark.parametrize(
    "test_input, expected",
    [("EMPLOYEE", 7), ("ACCOUNT", 123), ['PROJECT', 1086]],
)
@pytest.mark.django_db(databases=['default'])
def test_destination_attribute_count_view(test_input, expected, api_client, test_connection):

   access_token = test_connection.access_token
   url = reverse('attributes-count',
      kwargs={
         'workspace_id': 1
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url, {
      'attribute_type': test_input
   })
   assert response.status_code == 200
   response = json.loads(response.content)
   
   assert response['count'] == expected


def test_custom_segment_view(api_client, test_connection):

   access_token = test_connection.access_token
   url = reverse('custom-segments',
      kwargs={
         'workspace_id': 2
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)
   
   assert len(response) == 0


def test_trigger_export_view(api_client, test_connection):

   access_token = test_connection.access_token
   url = reverse('trigger-exports',
      kwargs={
         'workspace_id': 1
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   export_types = ['BILL', 'EXPENSE REPORT', 'JOURNAL ENTRY', 'CREDIT CARD CHARGE']

   for export_type in export_types:
      response = api_client.post(url, 
            data={
               'export_type': export_type
            }
      )

      assert response.status_code == 200

   
def test_trigger_payment_view(api_client, test_connection, add_fyle_credentials):

   access_token = test_connection.access_token
   url = reverse('trigger-payments',
      kwargs={
         'workspace_id': 2
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.post(url)
   assert response.status_code == 200


def test_sync_netsuite_dimensions(api_client, test_connection, add_netsuite_credentials):

   access_token = test_connection.access_token
   url = reverse('sync-dimensions',
      kwargs={
         'workspace_id': 2
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)

   assert response.status_code == 200

   netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=2)
   netsuite_credentials.delete()

   response = api_client.post(url)

   assert response.status_code == 400
   assert response.data['message'] == 'NetSuite credentials not found in workspace'


def test_refresh_netsuite_dimensions(api_client, test_connection, add_netsuite_credentials):

   access_token = test_connection.access_token
   url = reverse('refresh-dimensions',
      kwargs={
         'workspace_id': 2
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)

   assert response.status_code == 200

   netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=2)
   netsuite_credentials.delete()

   response = api_client.post(url)

   assert response.status_code == 400
   assert response.data['message'] == 'NetSuite credentials not found in workspace'
