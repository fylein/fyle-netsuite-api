import json
import logging

from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from netsuitesdk.internal.exceptions import NetSuiteRequestError

from fyle_accounting_mappings.models import DestinationAttribute
from fyle_accounting_mappings.serializers import DestinationAttributeSerializer

from fyle_netsuite_api.utils import assert_valid

from apps.fyle.models import ExpenseGroup
from apps.tasks.models import TaskLog
from apps.workspaces.models import NetSuiteCredentials

from .serializers import BillSerializer, ExpenseReportSerializer, JournalEntrySerializer, NetSuiteFieldSerializer, \
    CustomSegmentSerializer
from .tasks import schedule_bills_creation, create_bill, schedule_expense_reports_creation, create_expense_report, \
    create_journal_entry, schedule_journal_entry_creation, create_vendor_payment, check_netsuite_object_status, \
    process_reimbursements
from .models import Bill, ExpenseReport, JournalEntry, CustomSegment
from .utils import NetSuiteConnector

logger = logging.getLogger(__name__)


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

            accounts = ns_connector.sync_accounts()

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


class AccountsPayableView(generics.ListAPIView):
    """
    AccountsPayable view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='ACCOUNTS_PAYABLE', workspace_id=self.kwargs['workspace_id']).order_by('value')


class CreditCardAccountView(generics.ListAPIView):
    """
    CreditCardAccount view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='CREDIT_CARD_ACCOUNT', workspace_id=self.kwargs['workspace_id']).order_by('value')


class BankAccountView(generics.ListAPIView):
    """
    BankAccount view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='BANK_ACCOUNT', workspace_id=self.kwargs['workspace_id']).order_by('value')


class VendorPaymentAccountView(generics.ListAPIView):
    """
    VendorPaymentAccount view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='VENDOR_PAYMENT_ACCOUNT', workspace_id=self.kwargs['workspace_id']).order_by('value')


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


class ExpenseCategoryView(generics.ListCreateAPIView):
    """
    Expense Category view
    """

    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='EXPENSE_CATEGORY', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get Expense Category from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            expense_categories = ns_connector.sync_expense_categories()
            return Response(
                data=self.serializer_class(expense_categories, many=True).data,
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


class CurrencyView(generics.ListCreateAPIView):
    """
    Location view
    """

    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
        return DestinationAttribute.objects.filter(
            attribute_type='CURRENCY', workspace_id=self.kwargs['workspace_id']).order_by('value')

    def post(self, request, *args, **kwargs):
        """
        Get Expense Category from NetSuite
        """
        try:
            ns_credentials = NetSuiteCredentials.objects.get(workspace_id=kwargs['workspace_id'])

            ns_connector = NetSuiteConnector(ns_credentials, workspace_id=kwargs['workspace_id'])

            currencies = ns_connector.sync_currencies()
            return Response(
                data=self.serializer_class(currencies, many=True).data,
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
            kwargs['workspace_id'], expense_group_ids)

        return Response(
            status=status.HTTP_200_OK
        )


class ExpenseReportView(generics.ListCreateAPIView):
    """
    Create Expense Report
    """
    serializer_class = ExpenseReportSerializer

    def get_queryset(self):
        return ExpenseReport.objects.filter(
            expense_group__workspace_id=self.kwargs['workspace_id']
        ).order_by('-updated_at')

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
            kwargs['workspace_id'], expense_group_ids)

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
    serializer_class = CustomSegmentSerializer

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


class VendorPaymentView(generics.ListCreateAPIView):
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


class ReimburseNetSuitePaymentsView(generics.ListCreateAPIView):
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
