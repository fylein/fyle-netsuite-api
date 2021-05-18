import json
import logging
from datetime import datetime, timezone

from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from netsuitesdk.internal.exceptions import NetSuiteRequestError

from fyle_accounting_mappings.models import DestinationAttribute
from fyle_accounting_mappings.serializers import DestinationAttributeSerializer

from fyle_netsuite_api.utils import assert_valid

from apps.workspaces.models import NetSuiteCredentials, Workspace

from .serializers import NetSuiteFieldSerializer, CustomSegmentSerializer
from .tasks import schedule_bills_creation, schedule_expense_reports_creation, schedule_journal_entry_creation,\
    create_vendor_payment, check_netsuite_object_status, process_reimbursements
from .models import CustomSegment
from .utils import NetSuiteConnector

logger = logging.getLogger(__name__)


class SubsidiaryView(generics.ListCreateAPIView):
    """
    Subsidiary view
    """

    def post(self, request, *args, **kwargs):
        """
        Sync subsidiaries from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            subsidiaries = ns_connector.sync_subsidiaries()

            return Response(
                data=DestinationAttributeSerializer(subsidiaries, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except NetSuiteRequestError as exception:
            logger.exception({'error': exception})
            detail = json.dumps(exception.__dict__)
            detail = json.loads(detail)

            return Response(
                data={
                    'message': '{0} - {1}'.format(detail['code'], detail['message'])
                },
                status=status.HTTP_401_UNAUTHORIZED
            )


class BillScheduleView(generics.CreateAPIView):
    """
    Schedule bills creation
    """

    def post(self, request, *args, **kwargs):
        expense_group_ids = request.data.get('expense_group_ids', [])

        schedule_bills_creation(
            kwargs['workspace_id'], expense_group_ids)

        return Response(
            status=status.HTTP_200_OK
        )


class ExpenseReportScheduleView(generics.CreateAPIView):
    """
    Schedule expense reports creation
    """

    def post(self, request, *args, **kwargs):
        expense_group_ids = request.data.get('expense_group_ids', [])

        schedule_expense_reports_creation(
            kwargs['workspace_id'], expense_group_ids)

        return Response(
            status=status.HTTP_200_OK
        )


class JournalEntryScheduleView(generics.CreateAPIView):
    """
    Schedule JournalEntry creation
    """

    def post(self, request, *args, **kwargs):
        expense_group_ids = request.data.get('expense_group_ids', [])

        schedule_journal_entry_creation(
            kwargs['workspace_id'], expense_group_ids)

        return Response(
            status=status.HTTP_200_OK
        )


class NetSuiteFieldsView(generics.ListAPIView):
    pagination_class = None
    serializer_class = NetSuiteFieldSerializer

    def get_queryset(self):
        attributes = DestinationAttribute.objects.filter(
            ~Q(attribute_type='EMPLOYEE') & ~Q(attribute_type='ACCOUNT') &
            ~Q(attribute_type='VENDOR') & ~Q(attribute_type='ACCOUNTS_PAYABLE') &
            ~Q(attribute_type='VENDOR_PAYMENT_ACCOUNT') & ~Q(attribute_type='CCC_EXPENSE_CATEGORY') &
            ~Q(attribute_type='EXPENSE_CATEGORY') & ~Q(attribute_type='BANK_ACCOUNT') &
            ~Q(attribute_type='CREDIT_CARD_ACCOUNT') & ~Q(attribute_type='BANK_ACCOUNT') &
            ~Q(attribute_type='SUBSIDIARY') & ~Q(attribute_type='CURRENCY') &
            ~Q(attribute_type='CCC_ACCOUNT'),
            workspace_id=self.kwargs['workspace_id']
        ).values('attribute_type', 'display_name').distinct()

        return attributes


class SyncCustomFieldsView(generics.ListCreateAPIView):
    """
    SyncCustomFields view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        attribute_type = self.request.query_params.get('attribute_type')

        return DestinationAttribute.objects.filter(
            attribute_type=attribute_type, workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get Expense Category from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])
            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            all_custom_list = CustomSegment.objects.filter(workspace_id=kwargs['workspace_id']).all()

            custom_lists = ns_connector.sync_custom_segments(all_custom_list)

            return Response(
                data=self.serializer_class(custom_lists, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except NetSuiteRequestError as exception:
            logger.exception({'error': exception})
            detail = json.dumps(exception.__dict__)
            detail = json.loads(detail)

            return Response(
                data={
                    'message': '{0} - {1}'.format(detail['code'], detail['message'])
                },
                status=status.HTTP_401_UNAUTHORIZED
            )


class CustomSegmentView(generics.ListCreateAPIView):
    """
    CustomSegment view
    """
    pagination_class = None

    def get(self, request, *args, **kwargs):
        custom_lists = CustomSegment.objects.filter(workspace_id=self.kwargs['workspace_id']).all()

        return Response(
            data=CustomSegmentSerializer(custom_lists, many=True).data,
            status=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):
        """
        Validate Custom List from NetSuite
        """
        try:
            segment_type = request.data.get('segment_type')
            script_id = request.data.get('script_id')
            internal_id = request.data.get('internal_id')

            assert_valid(segment_type is not None, 'Segment type not found')
            assert_valid(script_id is not None, 'Script ID not found')
            assert_valid(internal_id is not None, 'Internal ID not found')

            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])
            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            if segment_type == 'CUSTOM_LIST':
                custom_list = ns_connector.connection.custom_lists.get(internal_id)

                CustomSegment.objects.update_or_create(
                    workspace_id=kwargs['workspace_id'],
                    internal_id=internal_id,
                    defaults={
                        'name': custom_list['name'].upper().replace(' ', '_'),
                        'script_id': script_id,
                        'segment_type': segment_type
                    }
                )

            elif segment_type == 'CUSTOM_RECORD':
                custom_record = ns_connector.connection.custom_records.get_all_by_id(internal_id)

                CustomSegment.objects.update_or_create(
                    workspace_id=kwargs['workspace_id'],
                    internal_id=internal_id,
                    defaults={
                        'name': custom_record[0]['recType']['name'].upper().replace(' ', '_'),
                        'script_id': script_id,
                        'segment_type': segment_type
                    }
                )

            return Response(
                status=status.HTTP_200_OK
            )

        except NetSuiteRequestError as exception:
            logger.exception({'error': exception})
            detail = json.dumps(exception.__dict__)
            detail = json.loads(detail)

            return Response(
                data={
                    'message': '{0} - {1}'.format(detail['code'], detail['message'])
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        except Exception as e:
            logger.exception(e)
            detail = json.dumps(e.__dict__)
            detail = json.loads(detail)

            return Response(
                data={
                    'message': '{0} - {1}'.format(detail['code'], detail['message'])
                },
                status=status.HTTP_401_UNAUTHORIZED
            )


class VendorPaymentView(generics.CreateAPIView):
    """
    Create Vendor Payment View
    """
    def post(self, request, *args, **kwargs):
        """
        Create vendor payment
        """
        create_vendor_payment(workspace_id=self.kwargs['workspace_id'])

        return Response(
            data={},
            status=status.HTTP_200_OK
        )


class ReimburseNetSuitePaymentsView(generics.CreateAPIView):
    """
    Reimburse NetSuite Payments View
    """
    def post(self, request, *args, **kwargs):
        """
        Process Reimbursements in Fyle
        """
        check_netsuite_object_status(workspace_id=self.kwargs['workspace_id'])
        process_reimbursements(workspace_id=self.kwargs['workspace_id'])

        return Response(
            data={},
            status=status.HTTP_200_OK
        )


class SyncNetSuiteDimensionView(generics.ListCreateAPIView):
    """
    Sync NetSuite Dimensions view
    """
    def post(self, request, *args, **kwargs):
        """
        Sync data from NetSuite
        """
        try:
            workspace = Workspace.objects.get(id=kwargs['workspace_id'])
            if workspace.destination_synced_at:
                time_interval = datetime.now(timezone.utc) - workspace.destination_synced_at

            if workspace.destination_synced_at is None or time_interval.days > 0:
                ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])
                ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

                ns_connector.sync_dimensions(kwargs['workspace_id'])

                workspace.destination_synced_at = datetime.now()
                workspace.save(update_fields=['destination_synced_at'])

            return Response(
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class RefreshNetSuiteDimensionView(generics.ListCreateAPIView):
    """
    Refresh NetSuite Dimensions view
    """
    def post(self, request, *args, **kwargs):
        """
        Sync data from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])
            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            ns_connector.sync_dimensions(kwargs['workspace_id'])

            workspace = Workspace.objects.get(id=kwargs['workspace_id'])
            workspace.destination_synced_at = datetime.now()
            workspace.save(update_fields=['destination_synced_at'])

            return Response(
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
