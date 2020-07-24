from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from fyle_accounting_mappings.models import DestinationAttribute
from fyle_accounting_mappings.serializers import DestinationAttributeSerializer

from fyle_netsuite_api.utils import assert_valid

from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog
from apps.workspaces.models import NetSuiteCredentials

from .serializers import BillSerializer, ExpenseReportSerializer, JournalEntrySerializer
from .tasks import schedule_bills_creation, create_bill, schedule_expense_reports_creation, create_expense_report, \
    create_journal_entry, schedule_journal_entry_creation
from .models import Bill, ExpenseReport, JournalEntry
from .utils import NetSuiteConnector


class DepartmentView(generics.ListCreateAPIView):
    """
    Department view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='DEPARTMENT', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get departments from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            departments = ns_connector.sync_departments()

            return Response(
                data=self.serializer_class(departments, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class VendorView(generics.ListCreateAPIView):
    """
    Vendor view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='VENDOR', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get vendors from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            vendors = ns_connector.sync_vendors()

            return Response(
                data=self.serializer_class(vendors, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class AccountView(generics.ListCreateAPIView):
    """
    Account view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='ACCOUNT', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get accounts from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            accounts = ns_connector.sync_accounts(account_type='_expense')

            return Response(
                data=self.serializer_class(accounts, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class AccountsPayableView(generics.ListCreateAPIView):
    """
    AccountsPayable view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='ACCOUNTS_PAYABLE', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get accounts from NetSuite
        """
        try:
            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(netsuite_credentials, workspace_id=kwargs['workspace_id'])

            accounts = ns_connector.sync_accounts(account_type='_accountsPayable')

            return Response(
                data=self.serializer_class(accounts, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class CreditCardAccountView(generics.ListCreateAPIView):
    """
    CreditCardAccount view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='CREDIT_CARD_ACCOUNT', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get credit card accounts from NetSuite
        """
        try:
            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(netsuite_credentials, workspace_id=kwargs['workspace_id'])

            accounts = ns_connector.sync_accounts(account_type='_creditCard')

            return Response(
                data=self.serializer_class(accounts, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class BankAccountView(generics.ListCreateAPIView):
    """
    BankAccount view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='BANK_ACCOUNT', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get bank accounts from NetSuite
        """
        try:
            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(netsuite_credentials, workspace_id=kwargs['workspace_id'])

            accounts = ns_connector.sync_expense_report_accounts()

            return Response(
                data=self.serializer_class(accounts, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class EmployeeView(generics.ListCreateAPIView):
    """
    Employee view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='EMPLOYEE', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get employees from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            employees = ns_connector.sync_employees()

            return Response(
                data=self.serializer_class(employees, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class LocationView(generics.ListCreateAPIView):
    """
    Location view
    """

    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='LOCATION', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get Locations from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            locations = ns_connector.sync_locations()
            return Response(
                data=self.serializer_class(locations, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ClassificationView(generics.ListCreateAPIView):
    """
    Classification view
    """

    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='CLASS', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get Classifications from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            classification = ns_connector.sync_classifications()
            return Response(
                data=self.serializer_class(classification, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class SubsidiaryView(generics.ListCreateAPIView):
    """
    Subsidiary view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self, **kwargs):
        return DestinationAttribute.objects.filter(
            attribute_type='SUBSIDIARY', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get subsidiaries from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            subsidiaries = ns_connector.sync_subsidiaries()

            return Response(
                data=self.serializer_class(subsidiaries, many=True).data,
                status=status.HTTP_200_OK
            )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite credentials not found in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class BillView(generics.ListCreateAPIView):
    """
    Create Bill
    """
    serializer_class = BillSerializer

    def get_queryset(self):
        return Bill.objects.filter(expense_group__workspace_id=self.kwargs['workspace_id']).order_by('-updated_at')

    def post(self, request, *args, **kwargs):
        """
        Create bill from expense group
        """
        expense_group_id = request.data.get('expense_group_id')
        task_log_id = request.data.get('task_log_id')

        assert_valid(expense_group_id is not None, 'expense group id not found')
        assert_valid(task_log_id is not None, 'Task Log id not found')

        expense_group = ExpenseGroup.objects.get(pk=expense_group_id)
        task_log = TaskLog.objects.get(pk=task_log_id)

        create_bill(expense_group, task_log)

        return Response(
            data={},
            status=status.HTTP_200_OK
        )


class BillScheduleView(generics.CreateAPIView):
    """
    Schedule bills creation
    """

    def post(self, request, *args, **kwargs):
        expense_group_ids = request.data.get('expense_group_ids', [])

        schedule_bills_creation(
            kwargs['workspace_id'], expense_group_ids, request.user)

        return Response(
            status=status.HTTP_200_OK
        )


class ExpenseReportView(generics.ListCreateAPIView):
    """
    Create Expense Report
    """
    serializer_class = ExpenseReportSerializer

    def get_queryset(self):
        return ExpenseReport.objects.filter(expense_group__workspace_id=self.kwargs['workspace_id']).order_by('-updated_at')

    def post(self, request, *args, **kwargs):
        """
        Create expense report from expense group
        """
        expense_group_id = request.data.get('expense_group_id')
        task_log_id = request.data.get('task_log_id')

        assert_valid(expense_group_id is not None, 'expense group id not found')
        assert_valid(task_log_id is not None, 'Task Log id not found')

        expense_group = ExpenseGroup.objects.get(pk=expense_group_id)
        task_log = TaskLog.objects.get(pk=task_log_id)

        create_expense_report(expense_group, task_log)

        return Response(
            data={},
            status=status.HTTP_200_OK
        )


class ExpenseReportScheduleView(generics.CreateAPIView):
    """
    Schedule expense reports creation
    """

    def post(self, request, *args, **kwargs):
        expense_group_ids = request.data.get('expense_group_ids', [])

        schedule_expense_reports_creation(
            kwargs['workspace_id'], expense_group_ids, request.user)

        return Response(
            status=status.HTTP_200_OK
        )


class JournalEntryView(generics.ListCreateAPIView):
    """
    Create JournalEntry
    """
    serializer_class = JournalEntrySerializer

    def get_queryset(self):
        return JournalEntry.objects.filter(
            expense_group__workspace_id=self.kwargs['workspace_id']
        ).order_by('-updated_at')

    def post(self, request, *args, **kwargs):
        """
        Create JournalEntry from expense group
        """
        expense_group_id = request.data.get('expense_group_id')
        task_log_id = request.data.get('task_log_id')

        assert_valid(expense_group_id is not None, 'Expense ids not found')
        assert_valid(task_log_id is not None, 'Task Log id not found')

        expense_group = ExpenseGroup.objects.get(pk=expense_group_id)
        task_log = TaskLog.objects.get(pk=task_log_id)

        create_journal_entry(expense_group, task_log)

        return Response(
            data={},
            status=status.HTTP_200_OK
        )


class JournalEntryScheduleView(generics.CreateAPIView):
    """
    Schedule JournalEntry creation
    """

    def post(self, request, *args, **kwargs):
        expense_group_ids = request.data.get('expense_group_ids', [])

        schedule_journal_entry_creation(
            kwargs['workspace_id'], expense_group_ids, request.user)

        return Response(
            status=status.HTTP_200_OK
        )
