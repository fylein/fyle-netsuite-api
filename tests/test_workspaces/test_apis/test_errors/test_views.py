import json
from datetime import datetime,timezone
from apps.tasks.models import Error
from .fixtures import data
from tests.helper import dict_compare_keys
import pytest
from django.urls import reverse

@pytest.mark.django_db(databases=['default'])
def test_errors(api_client, access_token):

    Error.objects.create(
        workspace_id=1, 
        type = 'EMPLOYEE_MAPPING',
        expense_attribute_id=8, 
        is_resolved = False,
        error_title = 'ashwin.t@fyle.in',
        error_detail = 'Employee mapping is missing',
        created_at = datetime.now(tz=timezone.utc),
        updated_at = datetime.now(tz=timezone.utc)
    )

    url = reverse(
        'errors', kwargs={
            'workspace_id': 1
        }
    )
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
    response = api_client.get(
        url,
        format='json'
    )

    assert response.status_code == 200

    response = json.loads(response.content)
    assert dict_compare_keys(response, data['errors_response']) == [], 'errors api returns a diff in the keys'

    url = '/api/v2/workspaces/1/errors/?is_resolved=False&type=CATEGORY_MAPPING'
    response = api_client.get(
        url,
        format='json'
    )

    assert response.status_code == 200

    Error.objects.filter(
        workspace_id=1,
        type='EMPLOYEE_MAPPING',
        error_detail = 'Employee mapping is missing',
        is_resolved=False
    ).update(is_resolved=True)

    url = '/api/v2/workspaces/1/errors/?is_resolved=true&type=EMPLOYEE_MAPPING'
    response = api_client.get(
        url,
        format='json'
    )

    assert response.status_code == 200
