import logging

from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status


from fyle_accounting_mappings.models import DestinationAttribute
from fyle_accounting_mappings.serializers import DestinationAttributeSerializer
from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum

from apps.workspaces.models import NetSuiteCredentials, Workspace, Configuration
from netsuitesdk import NetSuiteLoginError
from fyle_netsuite_api.utils import invalidate_netsuite_credentials

from django_q.tasks import async_task

from .serializers import NetSuiteFieldSerializer, CustomSegmentSerializer
from .tasks import create_vendor_payment, check_netsuite_object_status, process_reimbursements
from .models import CustomSegment
from .helpers import check_if_task_exists_in_ormq, handle_refresh_dimensions
from apps.workspaces.actions import export_to_netsuite

logger = logging.getLogger(__name__)


class TriggerExportsView(generics.GenericAPIView):
    """
    Trigger exports creation
    """
    def post(self, request, *args, **kwargs):
        export_to_netsuite(workspace_id=kwargs['workspace_id'], triggered_by=ExpenseImportSourceEnum.DASHBOARD_SYNC)

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
            ~Q(attribute_type='CCC_ACCOUNT') & ~Q(attribute_type='TAX_ITEM') & ~Q(attribute_type='PROJECT'),
            workspace_id=self.kwargs['workspace_id']
        ).values('attribute_type', 'display_name').distinct()

        attributes = list(attributes)
        attributes.append({
            'attribute_type': 'PROJECT',
            'display_name': 'Project'
        })

        return attributes


class DestinationAttributesView(generics.ListAPIView):
    """
    Destination Attributes view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        attribute_types = self.request.query_params.get('attribute_types').split(',')
        active = self.request.query_params.get('active')
        filters = {
            'attribute_type__in' : attribute_types,
            'workspace_id': self.kwargs['workspace_id']
        }

        if active and active.lower() == 'true':
            filters['active'] = True

        return DestinationAttribute.objects.filter(**filters).order_by('value')


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
            NetSuiteCredentials.get_active_netsuite_credentials(workspace.id)

            if not check_if_task_exists_in_ormq(func='apps.netsuite.helpers.check_interval_and_sync_dimension', payload=kwargs['workspace_id']):
                async_task('apps.netsuite.helpers.check_interval_and_sync_dimension', kwargs['workspace_id'])

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
        except NetSuiteLoginError:
            invalidate_netsuite_credentials(kwargs['workspace_id'])
            return Response(
                data={
                    'message': 'Invalid NetSuite credentials'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
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
            NetSuiteCredentials.get_active_netsuite_credentials(workspace.id)

            # If only specified dimensions are to be synced, sync them synchronously
            if dimensions_to_sync:
                handle_refresh_dimensions(kwargs['workspace_id'], dimensions_to_sync)
            else:
                if not check_if_task_exists_in_ormq(func='apps.netsuite.helpers.handle_refresh_dimensions', payload=kwargs['workspace_id']):
                    async_task('apps.netsuite.helpers.handle_refresh_dimensions', kwargs['workspace_id'], dimensions_to_sync)

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
        except NetSuiteLoginError:
            invalidate_netsuite_credentials(kwargs['workspace_id'])
            return Response(
                data={
                    'message': 'Invalid NetSuite credentials'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            return Response(
                data={
                    'message': 'Error in refreshing Dimensions'
                },
                status=status.HTTP_400_BAD_REQUEST
            )    
