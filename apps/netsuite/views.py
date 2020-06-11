from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import status

from fyle_accounting_mappings.models import DestinationAttribute
from fyle_accounting_mappings.serializers import DestinationAttributeSerializer

from apps.workspaces.models import NetSuiteCredentials

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


class SubsidiaryView(generics.ListCreateAPIView):
    """
    Subs view
    """
    serializer_class = DestinationAttributeSerializer
    pagination_class = None

    def get_queryset(self):
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
