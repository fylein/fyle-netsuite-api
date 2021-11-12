import pytest
import json
from django.urls import reverse

#  Will use paramaterize decorator of python later
@pytest.mark.django_db(databases=['default'])
def test_task_view(api_client, test_connection, create_task_logs):
    
   access_token = test_connection.access_token
   url = reverse('all-tasks', 
      kwargs={
            'workspace_id': 1,
        }
      )
   
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url, {
       'status': 'IN_PROGRESS'
   })
   assert response.status_code == 200
   response = json.loads(response.content)

   assert response['count'] == 1
