import json
import logging
from datetime import datetime

from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from netsuitesdk.internal.exceptions import NetSuiteRequestError

from fyle_accounting_mappings.models import DestinationAttribute
from fyle_accounting_mappings.serializers import DestinationAttributeSerializer

from fyle_netsuite_api.utils import assert_valid

from apps.workspaces.models import NetSuiteCredentials, Workspace, Configuration

from .serializers import NetSuiteFieldSerializer, CustomSegmentSerializer
from .tasks import schedule_bills_creation, schedule_expense_reports_creation, schedule_journal_entry_creation,\
    create_vendor_payment, check_netsuite_object_status, process_reimbursements, schedule_credit_card_charge_creation
from .models import CustomSegment
from .connector import NetSuiteConnector
from .helpers import check_interval_and_sync_dimension, sync_dimensions


logger = logging.getLogger(__name__)


class TriggerExportsView(generics.GenericAPIView):
    """
    Trigger exports creation
    """
    def post(self, request, *args, **kwargs):
        expense_group_ids = request.data.get('expense_group_ids', [])
        export_type = request.data.get('export_type')

        if export_type == 'BILL':
            schedule_bills_creation(kwargs['workspace_id'], expense_group_ids)
        elif export_type == 'CREDIT CARD CHARGE':
            schedule_credit_card_charge_creation(kwargs['workspace_id'], expense_group_ids)
        elif export_type == 'JOURNAL ENTRY':
            schedule_journal_entry_creation(kwargs['workspace_id'], expense_group_ids)
        elif export_type == 'EXPENSE REPORT':
            schedule_expense_reports_creation(kwargs['workspace_id'], expense_group_ids)

        return Response(
            status=status.HTTP_200_OK
        )


class TriggerPaymentsView(generics.GenericAPIView):
    """
    Trigger payments sync
    """
    def post(self, request, *args, **kwargs):
        configurations = Configuration.objects.get(workspace_id=kwargs['workspace_id'])

        if configurations.sync_fyle_to_netsuite_payments:
            create_vendor_payment(workspace_id=self.kwargs['workspace_id'])
        elif configurations.sync_netsuite_to_fyle_payments:
            check_netsuite_object_status(workspace_id=self.kwargs['workspace_id'])
            process_reimbursements(workspace_id=self.kwargs['workspace_id'])

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
            ~Q(attribute_type='CCC_ACCOUNT') & ~Q(attribute_type='TAX_ITEM'),
            workspace_id=self.kwargs['workspace_id']
        ).values('attribute_type', 'display_name').distinct()

        attributes = list(attributes)

        has_projects = False
        has_customers = False
        for attribute in attributes:
            if attribute['display_name'] == 'Project':
                has_projects = True
            elif attribute['display_name'] == 'Customer':
                has_customers = True

        if has_customers and not has_projects:
            attributes.append({
                'attribute_type': 'PROJECT',
                'display_name': 'Project'
            })
        
        attributes = list(filter(lambda attribute: attribute['display_name'] != 'Customer', attributes))

        return attributes


class DestinationAttributesView(generics.ListAPIView):
    """
    Destination Attributes view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        attribute_types = self.request.query_params.get('attribute_types').split(',')

        return DestinationAttribute.objects.filter(
            attribute_type__in=attribute_types, workspace_id=self.kwargs['workspace_id']).order_by('value')


class DestinationAttributesCountView(generics.RetrieveAPIView):
    """
    Destination Attributes Count view
    """
    def get(self, request, *args, **kwargs):
        attribute_type = self.request.query_params.get('attribute_type')

        attribute_count = DestinationAttribute.objects.filter(
            attribute_type=attribute_type, workspace_id=self.kwargs['workspace_id']
        ).count()

        return Response(
            data={
                'count': attribute_count
            },
            status=status.HTTP_200_OK
        )


class CustomSegmentView(generics.ListCreateAPIView):
    """
    CustomSegment view
    """
    pagination_class = None
    serializer_class = CustomSegmentSerializer
    queryset = CustomSegment.objects.all()

    def get(self, request, *args, **kwargs):
        custom_lists = CustomSegment.objects.filter(workspace_id=self.kwargs['workspace_id']).all()

        return Response(
            data=CustomSegmentSerializer(custom_lists, many=True).data,
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
            workspace = Workspace.objects.get(pk=kwargs['workspace_id'])
            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace.id)

            synced = check_interval_and_sync_dimension(workspace, netsuite_credentials)

            if synced:
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
        except Exception : 
            return Response(
                data={
                    'message': 'Error in syncing Dimensions'
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
            dimensions_to_sync = request.data.get('dimensions_to_sync', [])
            workspace = Workspace.objects.get(pk=kwargs['workspace_id'])

            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace.id)
            sync_dimensions(netsuite_credentials, workspace.id, dimensions_to_sync)

            # Update destination_synced_at to current time only when full refresh happens
            if not dimensions_to_sync:
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
        except Exception : 
            return Response(
                data={
                    'message': 'Error in refreshing Dimensions'
                },
                status=status.HTTP_400_BAD_REQUEST
            )    
