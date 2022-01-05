from os import access
from django.http import response
import pytest
import json

from django.urls import reverse
from apps.fyle.models import ExpenseGroup

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


@pytest.mark.parametrize(
    "test_input, expected",
    [("EMPLOYEE", 9), ("ACCOUNT", 123), ['PROJECT', 1087]],
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
