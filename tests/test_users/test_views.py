from django.urls import reverse
import pytest

from tests.test_fyle.fixtures import data as fyle_data

#  Will use paramaterize decorator of python later
@pytest.mark.django_db(databases=['default'])
def test_get_profile_view(api_client, access_token):
    
    url = reverse('profile')
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    assert response.status_code == 200
