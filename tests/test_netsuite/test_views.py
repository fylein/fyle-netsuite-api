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

   assert len(response) == 5
