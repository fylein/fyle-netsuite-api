import pytest
from django.test import TestCase
from django.core.cache import cache
from datetime import datetime, timezone
from fyle_netsuite_api.tests import settings
from apps.workspaces.models import Workspace, NetSuiteCredentials, FyleCredential, \
    WorkspaceSchedule, Configuration, FeatureConfig
from fyle_rest_auth.models import AuthToken, User


@pytest.mark.django_db
def test_workspace_creation():
    '''
    Test Post of User Profile
    '''
    user = User.objects.get(id=1)

    new_workspace = Workspace.objects.create(
        id=100,
        name='Fyle Test Org',
        fyle_org_id='nil123pant',
        ns_account_id=settings.NS_ACCOUNT_ID,
        last_synced_at=None,
        source_synced_at=None,
        destination_synced_at=None,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc)
    )
    new_workspace.user.add(user)

    workspace = Workspace.objects.get(id=100)

    assert workspace.fyle_org_id=='nil123pant'
    assert workspace.name=='Fyle Test Org'


@pytest.mark.django_db
def test_feature_config_get_cache_key():
    workspace_id = 1
    key = 'skip_posting_gross_amount'

    cache_key = FeatureConfig._get_cache_key(workspace_id, key)

    assert cache_key == f'skip_posting_gross_amount_{workspace_id}'


@pytest.mark.django_db
def test_feature_config_get_feature_config_skip_posting_gross_amount():
    workspace_id = 1
    key = 'skip_posting_gross_amount'
    cache_key = FeatureConfig._get_cache_key(workspace_id, key)

    cache.delete(cache_key)

    feature_config = FeatureConfig.objects.get(workspace_id=workspace_id)
    feature_config.skip_posting_gross_amount = True
    feature_config.save()

    assert cache.get(cache_key) is None

    value = FeatureConfig.get_feature_config(workspace_id, key)

    assert value is True
    assert cache.get(cache_key) is True

    feature_config.skip_posting_gross_amount = False
    feature_config.save()

    cached_value = FeatureConfig.get_feature_config(workspace_id, key)
    assert cached_value is True


@pytest.mark.django_db
def test_feature_config_reset_feature_config_cache_skip_posting_gross_amount():
    workspace_id = 1
    key = 'skip_posting_gross_amount'
    cache_key = FeatureConfig._get_cache_key(workspace_id, key)

    feature_config = FeatureConfig.objects.get(workspace_id=workspace_id)
    feature_config.skip_posting_gross_amount = True
    feature_config.save()

    cache.set(cache_key, True, 172800)
    assert cache.get(cache_key) is True

    feature_config.skip_posting_gross_amount = False
    feature_config.save()

    FeatureConfig.reset_feature_config_cache(workspace_id, key)

    assert cache.get(cache_key) is False