import pytest
from datetime import datetime, timezone
from fyle_rest_auth.models import User
from pytest_postgresql import factories

@pytest.mark.django_db
def test_user_creation(django_db_setup):
    '''
    Test Post of User Profile
    '''
    user = User(password='', last_login=datetime.now(tz=timezone.utc), email='nilesh.p@fyle.in',
                         user_id='ust5Gda9HC3qc', full_name='', active='t', staff='f', admin='t')

    user.save()

    assert user.email=='nilesh.p@fyle.in'


@pytest.mark.django_db
def test_get_of_user(add_users_to_database):
    '''
    Test Get of User Profile
    '''
    user = User.objects.filter(email='nilesh.p@fyle.in').first()

    assert user.user_id == 'ust5Gda9HC3qc'


    
