import logging
from datetime import datetime
from django.db.models import Q

from rest_framework.views import status
from rest_framework import generics
from rest_framework.response import Response

from fyle_integrations_platform_connector import PlatformConnector
from fyle_accounting_mappings.models import ExpenseAttribute
from fyle_accounting_mappings.serializers import ExpenseAttributeSerializer

from apps.workspaces.models import FyleCredential, Workspace

from .tasks import schedule_expense_group_creation
from .helpers import check_interval_and_sync_dimension, sync_dimensions
from .models import Expense, ExpenseGroup, ExpenseGroupSettings, ExpenseFilter
from .serializers import ExpenseGroupSerializer, ExpenseSerializer, ExpenseFieldSerializer, \
    ExpenseGroupSettingsSerializer, ExpenseFilterSerializer, ExpenseGroupExpenseSerializer
from .constants import DEFAULT_FYLE_CONDITIONS

from fyle.platform import Platform
from fyle_netsuite_api import settings

logger = logging.getLogger(__name__)
logger.level = logging.INFO
class ExpenseGroupView(generics.ListCreateAPIView):
    """
    List Fyle Expenses
    """
    serializer_class = ExpenseGroupSerializer

    def get_queryset(self):
        state = self.request.query_params.get('state')

        if state == 'FAILED':
            return ExpenseGroup.objects.filter(
                tasklog__status='FAILED', workspace_id=self.kwargs['workspace_id']).order_by('-updated_at')

        elif state == 'COMPLETE':
            return ExpenseGroup.objects.filter(
                tasklog__status='COMPLETE', workspace_id=self.kwargs['workspace_id']).order_by('-exported_at')

        elif state == 'READY':
            return ExpenseGroup.objects.filter(
                workspace_id=self.kwargs['workspace_id'],
                bill__id__isnull=True,
                expensereport__id__isnull=True,
                journalentry__id__isnull=True,
                creditcardcharge__id__isnull=True
            ).order_by('-updated_at')


class ExpenseGroupCountView(generics.ListAPIView):
    """
    Expense Group Count View
    """

    def get(self, request, *args, **kwargs):
        state_filter = {
            'tasklog__status': self.request.query_params.get('state')
        }
        expense_groups_count = ExpenseGroup.objects.filter(
            workspace_id=kwargs['workspace_id'], **state_filter
        ).count()

        return Response(
            data={'count': expense_groups_count},
            status=status.HTTP_200_OK
        )


class ExpenseGroupSettingsView(generics.ListCreateAPIView):
    """
    Expense Group Settings View
    """
    serializer_class = ExpenseGroupSettingsSerializer

    def get(self, request, *args, **kwargs):
        expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=self.kwargs['workspace_id'])

        return Response(
            data=self.serializer_class(expense_group_settings).data,
            status=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):
        expense_group_settings, _ = ExpenseGroupSettings.update_expense_group_settings(
            request.data, self.kwargs['workspace_id'])
        return Response(
            data=self.serializer_class(expense_group_settings).data,
            status=status.HTTP_200_OK
        )


class ExpenseAttributesView(generics.ListAPIView):
    """
    Expense Attributes view
    """
    serializer_class = ExpenseAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        attribute_type = self.request.query_params.get('attribute_type')
        active = self.request.query_params.get('active')
        filters = {
            'attribute_type' : attribute_type,
            'workspace_id': self.kwargs['workspace_id']
        }

        if active and active.lower() == 'true':
            filters['active'] = True

        return ExpenseAttribute.objects.filter(**filters).order_by('value')


class FyleFieldsView(generics.ListAPIView):
    pagination_class = None
    serializer_class = ExpenseFieldSerializer

    def get(self, request, *args, **kwargs):
        default_attributes = ['EMPLOYEE', 'CATEGORY', 'PROJECT', 'COST_CENTER', 'TAX_GROUP', 'CORPORATE_CARD', 'MERCHANT']

        attributes = ExpenseAttribute.objects.filter(
            ~Q(attribute_type__in=default_attributes),
            workspace_id=self.kwargs['workspace_id']
        ).values('attribute_type', 'display_name').distinct()

        expense_fields = [
            {'attribute_type': 'COST_CENTER', 'display_name': 'Cost Center'},
            {'attribute_type': 'PROJECT', 'display_name': 'Project'}
        ]

        for attribute in attributes:
            expense_fields.append(attribute)

        return Response(
            expense_fields,
            status=status.HTTP_200_OK
        )


class ExpenseGroupScheduleView(generics.CreateAPIView):
    """
    Create expense group schedule
    """
    def post(self, request, *args, **kwargs):
        """
        Post expense schedule
        """
        schedule_expense_group_creation(kwargs['workspace_id'])

        return Response(
            status=status.HTTP_200_OK
        )


class ExpenseGroupByIdView(generics.RetrieveAPIView):
    """
    Expense Group by Id view
    """
    serializer_class = ExpenseGroupSerializer
    queryset = ExpenseGroup.objects.all()


class ExpenseGroupExpenseView(generics.RetrieveAPIView):
    """
    ExpenseGroup Expense view
    """

    def get(self, request, *args, **kwargs):
        """
        Get expenses
        """
        try:
            expense_group = ExpenseGroup.objects.get(
                workspace_id=kwargs['workspace_id'], pk=kwargs['expense_group_id']
            )
            expenses = Expense.objects.filter(
                id__in=expense_group.expenses.values_list('id', flat=True)).order_by('-updated_at')
            return Response(
                data=ExpenseGroupExpenseSerializer(expenses, many=True).data,
                status=status.HTTP_200_OK
            )

        except ExpenseGroup.DoesNotExist:
            return Response(
                data={
                    'message': 'Expense group not found'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class SyncFyleDimensionView(generics.ListCreateAPIView):
    """
    Sync Fyle Dimensions view
    """
    def post(self, request, *args, **kwargs):
        """
        Sync data from Fyle
        """
        try:
            workspace = Workspace.objects.get(pk=kwargs['workspace_id'])
            fyle_credentials = FyleCredential.objects.get(workspace_id=workspace.id)

            synced = check_interval_and_sync_dimension(workspace, fyle_credentials)
            if synced:
                workspace.source_synced_at = datetime.now()
                workspace.save(update_fields=['source_synced_at'])

            return Response(
                status=status.HTTP_200_OK
            )
        except FyleCredential.DoesNotExist:
            return Response(
                data={
                    'message': 'Fyle credentials not found in workspace'
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


class RefreshFyleDimensionView(generics.ListCreateAPIView):
    """
    Refresh Fyle Dimensions view
    """
    def post(self, request, *args, **kwargs):
        """
        Sync data from Fyle
        """
        try:
            workspace = Workspace.objects.get(id=kwargs['workspace_id'])
            fyle_credentials = FyleCredential.objects.get(workspace_id=workspace.id)
            sync_dimensions(fyle_credentials, workspace.id)

            workspace.source_synced_at = datetime.now()
            workspace.save(update_fields=['source_synced_at'])

            return Response(
                status=status.HTTP_200_OK
            )
        except FyleCredential.DoesNotExist:
            return Response(
                data={
                    'message': 'Fyle credentials not found in workspace'
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


class ExpenseFilterView(generics.ListCreateAPIView, generics.DestroyAPIView):
    """
    Expense Filter view
    """
    serializer_class = ExpenseFilterSerializer

    def get_queryset(self):
        queryset = ExpenseFilter.objects.filter(workspace_id=self.kwargs['workspace_id']).order_by('rank')
        return queryset

    def delete(self, request, *args, **kwargs):
        try:
            workspace_id = self.kwargs['workspace_id']
            rank = self.request.query_params.get('rank')
            ExpenseFilter.objects.filter(workspace_id=workspace_id,rank=rank).delete()

            return Response(data={
                'workspace_id': workspace_id,
                'rank' : rank, 
                'message': 'Expense filter deleted'
            })

        except Exception as exception:
            logger.error(
                'Something went wrong - %s in Fyle %s %s',
                workspace_id, exception.message, {'error': exception.response}
            )
            return Response(
                data={
                    'message': 'Something went wrong'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ExpenseView(generics.ListAPIView):
    """
    Expense view
    """

    serializer_class = ExpenseSerializer

    def get_queryset(self):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        org_id = Workspace.objects.get(id=self.kwargs['workspace_id']).fyle_org_id

        filters = {
            'org_id': org_id,
            'is_skipped': True
        }

        if start_date and end_date:
            filters['updated_at__range'] = [start_date, end_date]

        queryset = Expense.objects.filter(**filters).order_by('-updated_at')

        return queryset


class CustomFieldView(generics.RetrieveAPIView):
    """
    Custom Field view
    """
    def get(self, request, *args, **kwargs):
        """
        Get Custom Fields
        """
        try:
            workspace_id = self.kwargs['workspace_id']
            fyle_credentails = FyleCredential.objects.get(workspace_id=workspace_id)
            platform = PlatformConnector(fyle_credentails)
            custom_fields = platform.expense_custom_fields.list_all()

            response = [] 
            response.extend(DEFAULT_FYLE_CONDITIONS)

            for custom_field in custom_fields:
                response.append({
                    'field_name': custom_field['field_name'],
                    'type': custom_field['type'],
                    'is_custom': custom_field['is_custom']
                })

            return Response(
                data=response,
                status=status.HTTP_200_OK
            )

        except Exception as exception:
            logger.error(
                'Something went wrong - %s in Fyle %s %s',
                workspace_id, exception.message, {'error': exception.response}
            )
            return Response(
                data={
                    'message': 'Something went wrong'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
