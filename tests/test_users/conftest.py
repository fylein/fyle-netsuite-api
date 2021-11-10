import pytest
from datetime import datetime, timezone
from fyle_rest_auth.models import User

@pytest.fixture
def add_users_to_database(db):
    user = User(password='', last_login=datetime.now(tz=timezone.utc), email='nilesh.p@fyle.in',
                         user_id='ust5Gda9HC3qc', full_name='', active='t', staff='f', admin='t')
    
    user.save()
