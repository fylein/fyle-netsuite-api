from django.urls import reverse
import pytest

from rest_framework.test import APITestCase, APIClient
from fyle_netsuite_api.tests.helpers import TestHelpers
from apps.users.models import User


def test_example_user():

    user = User.objects.filter(email='sravan.kumar@fyle.in').first()
    assert user.fyle_org_id == 'ust5Ga9HC3qc'

