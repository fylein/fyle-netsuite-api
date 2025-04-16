from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fyle_rest_auth.models import AuthToken

from fyle_integrations_platform_connector import PlatformConnector

from apps.workspaces.models import FyleCredential
from apps.fyle.helpers import get_fyle_orgs
from apps.users.helpers import get_cluster_domain_and_refresh_token


class UserProfileView(generics.RetrieveAPIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get User Details
        """
        
        refresh_token = AuthToken.objects.get(user__user_id=request.user).refresh_token

        cluster_domain, _ = get_cluster_domain_and_refresh_token(request.user)

        fyle_credentials = FyleCredential(
            cluster_domain=cluster_domain,
            refresh_token=refresh_token
        )

        platform = PlatformConnector(fyle_credentials)
        employee_profile = platform.connection.v1.spender.my_profile.get()

        return Response(
            data=employee_profile,
            status=status.HTTP_200_OK
        )


class FyleOrgsView(generics.ListCreateAPIView):
    """
    FyleOrgs view
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get cluster domain from Fyle
        """
        cluster_domain, refresh_token = get_cluster_domain_and_refresh_token(request.user)
        fyle_orgs = get_fyle_orgs(refresh_token, cluster_domain)

        return Response(
            data=fyle_orgs,
            status=status.HTTP_200_OK
        )
