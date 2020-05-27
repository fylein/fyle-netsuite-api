from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fyle_rest_auth.models import AuthToken

from apps.fyle.utils import FyleConnector


class UserProfileView(generics.RetrieveAPIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get User Details
        """
        fyle_credentials = AuthToken.objects.get(user__user_id=request.user)

        fyle_connector = FyleConnector(fyle_credentials.refresh_token)

        employee_profile = fyle_connector.get_employee_profile()

        return Response(
            data=employee_profile,
            status=status.HTTP_200_OK
        )
