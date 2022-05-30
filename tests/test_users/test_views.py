from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from fyle_rest_auth.models import User
import pytest

#  Will use paramaterize decorator of python later
@pytest.mark.django_db(databases=['default'])
def test_get_profile_view(api_client, access_token):
    
    url = reverse('profile')
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db(databases=['default'])
def test_get_fyle_orgs_view(api_client, access_token):
    url = reverse('orgs')
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    assert response.status_code == 200
