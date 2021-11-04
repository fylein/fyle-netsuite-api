from django.urls import reverse
from datetime import datetime, timezone
import pytest

from fyle_netsuite_api.tests import settings
from rest_framework.test import APITestCase, APIClient
from fyle_rest_auth.models import AuthToken, User
from fylesdk import FyleSDK

from apps.workspaces.models import Workspace

from pytest_postgresql import factories
from fyle_netsuite_api.tests.helpers import django_db_setup, test_connection

@pytest.mark.django_db
def test_user_creation():
    '''
    Test Post of User Profile
    '''
    user = User(password='', last_login=datetime.now(tz=timezone.utc), email='nilesh.p@fyle.in',
                         user_id='ust5Gda9HC3qc', full_name='', active='t', staff='f', admin='t')

    user.save()

    assert user.email=='nilesh.p@fyle.in'


@pytest.mark.django_db
def test_get_of_user():
    '''
    Test Get of User Profile
    '''
    user = User.objects.filter(email='sravan.kumar@fyle.in').first()

    assert user.user_id == 'ust5Ga9HC3qc'


    
