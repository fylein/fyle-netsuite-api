from django.urls import reverse

from rest_framework.test import APITestCase, APIClient

from fyle_netsuite_api.tests.helpers import django_db_setup, test_connection
from fyle_rest_auth.models import User
import pytest

@pytest.fixture
def api_client():
   from rest_framework.test import APIClient
   return APIClient()


#  Will use paramaterize decorator of python later

@pytest.mark.django_db(databases=['cache_db', 'default'])
def test_get_profile_view(api_client, django_db_setup, test_connection):
    
    access_token = test_connection.access_token
    url = reverse('profile')
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db(databases=['cache_db', 'default'])
def test_get_cluster_domain_view(api_client, test_connection):
    access_token = test_connection.access_token
    url = reverse('domain')
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    assert response.status_code == 200
    assert response.content == b'"https://staging.fyle.tech"'

@pytest.mark.django_db(databases=['cache_db', 'default'])
def test_get_fyle_orgs_view(api_client, test_connection):
    access_token = test_connection.access_token
    url = reverse('orgs')
    api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

    response = api_client.get(url)
    assert response.status_code == 200
