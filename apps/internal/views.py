import logging
import traceback
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status

from apps.workspaces.permissions import IsAuthenticatedForInternalAPI

from fyle_netsuite_api.utils import assert_valid

from .actions import get_accounting_fields, get_exported_entry

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AccountingFieldsView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [IsAuthenticatedForInternalAPI]

    def get(self, request, *args, **kwargs):
        try:
            params = request.query_params

            assert_valid(params.get('org_id') is not None, 'Org ID is required')
            assert_valid(params.get('resource_type') is not None, 'Resource Type is required')

            if params.get('resource_type') in ('custom_segments', 'custom_lists', 'custom_record_types'):
                assert_valid(params.get('internal_id') is not None, 'Internal ID is required')

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


class ExportedEntryView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [IsAuthenticatedForInternalAPI]

    def get(self, request, *args, **kwargs):
        try:
            params = request.query_params
            assert_valid(params.get('org_id') is not None, 'Org ID is required')
            assert_valid(params.get('resource_type') is not None, 'Resource Type is required')
            assert_valid(params.get('internal_id') is not None, 'Internal ID is required')

            response = get_exported_entry(request.query_params)

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
