import logging
import traceback
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status

from apps.workspaces.permissions import IsAuthenticatedForInternalAPI

from .actions import get_accounting_fields

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AccountingFieldsView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [IsAuthenticatedForInternalAPI]

    def get(self, request, *args, **kwargs):
        try:
            response = get_accounting_fields(request.query_params)
            return Response(
                data={'data': response},
                status=status.HTTP_200_OK
            )
        except Exception:
            logger.info(f"Error in AccountingFieldsView: {traceback.format_exc()}")
            return Response(
                data={'error': traceback.format_exc()},
                status=status.HTTP_400_BAD_REQUEST
            )
