from typing import Tuple

from fyle_rest_auth.models import AuthToken

from apps.fyle.helpers import get_cluster_domain
from apps.workspaces.models import FyleCredential


def get_cluster_domain_and_refresh_token(user) -> Tuple[str, str]:
    """
    Get cluster domain and refresh token from User
    """
    fyle_credentials = FyleCredential.objects.filter(workspace__user=user).first()

    if fyle_credentials:
        refresh_token = fyle_credentials.refresh_token
        cluster_domain = fyle_credentials.cluster_domain
    else:
        refresh_token = AuthToken.objects.get(user__user_id=user).refresh_token
        cluster_domain = get_cluster_domain(refresh_token)

    return cluster_domain, refresh_token
