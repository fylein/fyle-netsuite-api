from django.db.models import Q

from rest_framework.views import status
from rest_framework import generics
from rest_framework.response import Response

from fyle_accounting_mappings.models import ExpenseAttribute
from fyle_accounting_mappings.serializers import ExpenseAttributeSerializer

from apps.tasks.models import TaskLog
from apps.workspaces.models import FyleCredential, WorkspaceGeneralSettings

from .tasks import create_expense_groups, schedule_expense_group_creation
from .utils import FyleConnector
from .models import Expense, ExpenseGroup, ExpenseGroupSettings
from .serializers import ExpenseGroupSerializer, ExpenseSerializer, ExpenseFieldSerializer, \
    ExpenseGroupSettingsSerializer


class ExpenseGroupView(generics.ListCreateAPIView):
    """
    List Fyle Expenses
    """
    serializer_class = ExpenseGroupSerializer

    def get_queryset(self):
        state = self.request.query_params.get('state', 'ALL')

        if state == 'ALL':
            return ExpenseGroup.objects.filter(workspace_id=self.kwargs['workspace_id']).order_by('-updated_at')

        if state == 'FAILED':
            return ExpenseGroup.objects.filter(tasklog__status='FAILED',
                                               workspace_id=self.kwargs['workspace_id']).order_by('-updated_at')

        elif state == 'COMPLETE':
            return ExpenseGroup.objects.filter(tasklog__status='COMPLETE',
                                               workspace_id=self.kwargs['workspace_id']).order_by('-exported_at')

        elif state == 'READY':
            return ExpenseGroup.objects.filter(
                workspace_id=self.kwargs['workspace_id'],
                bill__id__isnull=True,
                expensereport__id__isnull=True,
                journalentry__id__isnull=True
            ).order_by('-updated_at')

    def post(self, request, *args, **kwargs):
        """
        Create expense groups
        """
        task_log = TaskLog.objects.get(pk=request.data.get('task_log_id'))

        general_settings = WorkspaceGeneralSettings.objects.get(workspace_id=kwargs['workspace_id'])

        fund_source = ['PERSONAL']
        if general_settings.corporate_credit_card_expenses_object is not None:
            fund_source.append('CCC')

        create_expense_groups(
            kwargs['workspace_id'],
            fund_source=fund_source,
            task_log=task_log
        )

        return Response(
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


class ExpenseCustomFieldsView(generics.ListCreateAPIView):
    """
    Project view
    """
    serializer_class = ExpenseAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        attribute_type = self.request.query_params.get('attribute_type')

        return ExpenseAttribute.objects.filter(
            attribute_type=attribute_type, workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get Expense Custom Fields from Fyle
        """
        try:
            active_only = request.GET.get('active_only', True)
            fyle_credentials = FyleCredential.objects.get(
                workspace_id=kwargs['workspace_id'])

            fyle_connector = FyleConnector(fyle_credentials.refresh_token, kwargs['workspace_id'])

            expense_custom_field_attributes = fyle_connector.sync_expense_custom_fields(active_only=active_only)

            return Response(
                data=self.serializer_class(expense_custom_field_attributes, many=True).data,
                status=status.HTTP_200_OK
            )
        except FyleCredential.DoesNotExist:
            return Response(
                data={
                    'message': 'Fyle credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ExpenseFieldsView(generics.ListAPIView):
    pagination_class = None
    serializer_class = ExpenseFieldSerializer

    def get_queryset(self):
        attributes = ExpenseAttribute.objects.filter(
            ~Q(attribute_type='EMPLOYEE') & ~Q(attribute_type='CATEGORY'),
            workspace_id=self.kwargs['workspace_id']
        ).values('attribute_type', 'display_name').distinct()

        return attributes


class ExpenseGroupScheduleView(generics.CreateAPIView):
    """
    Create expense group schedule
    """

    def post(self, request, *args, **kwargs):
        """
        Post expense schedule
        """
        schedule_expense_group_creation(kwargs['workspace_id'], request.user)

        return Response(
            status=status.HTTP_200_OK
        )


class ExpenseGroupByIdView(generics.RetrieveAPIView):
    """
    Expense Group by Id view
    """

    def get(self, request, *args, **kwargs):
        """
        Get expenses
        """
        try:
            expense_group = ExpenseGroup.objects.get(
                workspace_id=kwargs['workspace_id'], pk=kwargs['expense_group_id']
            )

            return Response(
                data=ExpenseGroupSerializer(expense_group).data,
                status=status.HTTP_200_OK
            )

        except ExpenseGroup.DoesNotExist:
            return Response(
                data={
                    'message': 'Expense group not found'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ExpenseView(generics.RetrieveAPIView):
    """
    Expense view
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
                data=ExpenseSerializer(expenses, many=True).data,
                status=status.HTTP_200_OK
            )

        except ExpenseGroup.DoesNotExist:
            return Response(
                data={
                    'message': 'Expense group not found'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class EmployeeView(generics.ListCreateAPIView):
    """
    Employee view
    """

    serializer_class = ExpenseAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return ExpenseAttribute.objects.filter(
            attribute_type='EMPLOYEE', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get employees from Fyle
        """
        try:
            fyle_credentials = FyleCredential.objects.get(
                workspace_id=kwargs['workspace_id'])

            fyle_connector = FyleConnector(fyle_credentials.refresh_token, kwargs['workspace_id'])

            employee_attributes = fyle_connector.sync_employees()

            return Response(
                data=self.serializer_class(employee_attributes, many=True).data,
                status=status.HTTP_200_OK
            )
        except FyleCredential.DoesNotExist:
            return Response(
                data={
                    'message': 'Fyle credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class CategoryView(generics.ListCreateAPIView):
    """
    Category view
    """

    serializer_class = ExpenseAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return ExpenseAttribute.objects.filter(
            attribute_type='CATEGORY', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get categories from Fyle
        """
        try:
            active_only = request.GET.get('active_only', False)
            fyle_credentials = FyleCredential.objects.get(
                workspace_id=kwargs['workspace_id'])

            fyle_connector = FyleConnector(fyle_credentials.refresh_token, kwargs['workspace_id'])

            category_attributes = fyle_connector.sync_categories(active_only=active_only)

            return Response(
                data=self.serializer_class(category_attributes, many=True).data,
                status=status.HTTP_200_OK
            )
        except FyleCredential.DoesNotExist:
            return Response(
                data={
                    'message': 'Fyle credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class CostCenterView(generics.ListCreateAPIView):
    """
    Category view
    """

    serializer_class = ExpenseAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return ExpenseAttribute.objects.filter(
            attribute_type='COST_CENTER', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get categories from Fyle
        """
        try:
            active_only = request.GET.get('active_only', False)
            fyle_credentials = FyleCredential.objects.get(
                workspace_id=kwargs['workspace_id'])

            fyle_connector = FyleConnector(fyle_credentials.refresh_token, kwargs['workspace_id'])

            cost_center_attributes = fyle_connector.sync_cost_centers(active_only=active_only)

            return Response(
                data=self.serializer_class(cost_center_attributes, many=True).data,
                status=status.HTTP_200_OK
            )
        except FyleCredential.DoesNotExist:
            return Response(
                data={
                    'message': 'Fyle credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ProjectView(generics.ListCreateAPIView):
    """
    Project view
    """
    serializer_class = ExpenseAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return ExpenseAttribute.objects.filter(
            attribute_type='PROJECT', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get categories from Fyle
        """
        try:
            active_only = request.GET.get('active_only', False)
            fyle_credentials = FyleCredential.objects.get(
                workspace_id=kwargs['workspace_id'])

            fyle_connector = FyleConnector(fyle_credentials.refresh_token, kwargs['workspace_id'])

            project_attributes = fyle_connector.sync_projects(active_only=active_only)

            return Response(
                data=self.serializer_class(project_attributes, many=True).data,
                status=status.HTTP_200_OK
            )
        except FyleCredential.DoesNotExist:
            return Response(
                data={
                    'message': 'Fyle credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
