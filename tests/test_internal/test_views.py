import pytest
from unittest.mock import patch
from django.urls import reverse

from apps.workspaces.permissions import IsAuthenticatedForInternalAPI

from tests.test_netsuite.fixtures import data


@pytest.mark.django_db(databases=['default'])
@patch.object(IsAuthenticatedForInternalAPI, 'has_permission', return_value=True)
def test_netsutie_fields_view(db, api_client, mocker):
    url = reverse('accounting-fields')

    response = api_client.get(url)
    assert response.status_code == 400

    response = api_client.get(url, {'org_id': 'or79Cob97KSh'})
    assert response.status_code == 400

    response = api_client.get(url, {'org_id': 'or79Cob97KSh', 'resource_type': 'custom_segments'})
    assert response.status_code == 400

    mocker.patch(
        'netsuitesdk.api.custom_lists.CustomLists.get',
        return_value=data['get_custom_list']
    )

    response = api_client.get(url, {'org_id': 'or79Cob97KSh', 'resource_type': 'custom_lists', 'internal_id': '1'})
    assert response.status_code == 200

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=data['get_all_employees']    
    )

    response = api_client.get(url, {'org_id': 'or79Cob97KSh', 'resource_type': 'employees'})
    assert response.status_code == 200
