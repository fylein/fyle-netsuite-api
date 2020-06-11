import itertools

from netsuitesdk import NetSuiteConnection

from apps.workspaces.models import NetSuiteCredentials

from fyle_accounting_mappings.models import DestinationAttribute


class NetSuiteConnector:
    """
    NetSuite utility functions
    """

    def __init__(self, netsuite_credentials: NetSuiteCredentials, workspace_id: int):
        self.connection = NetSuiteConnection(
            account=netsuite_credentials.ns_account_id,
            consumer_key=netsuite_credentials.ns_consumer_key,
            consumer_secret=netsuite_credentials.ns_consumer_secret,
            token_key=netsuite_credentials.ns_token_id,
            token_secret=netsuite_credentials.ns_token_secret
        )

        self.workspace_id = workspace_id

    def sync_accounts(self):
        """
        Get departments
        """
        accounts = list(itertools.islice(self.connection.accounts.get_all_generator(), 100))

        account_attributes = []

        for account in accounts:
            account_attributes.append({
                'attribute_type': 'ACCOUNT',
                'display_name': 'Account',
                'value': account['acctName'],
                'destination_id': account['acctName']
            })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            account_attributes, self.workspace_id)
        return account_attributes

    def sync_locations(self):
        """
        Get locations
        """
        locations = self.connection.locations.get_all()

        location_attributes = []

        for location in locations:
            location_attributes.append({
                'attribute_type': 'LOCATION',
                'display_name': 'Location',
                'value': location['name'],
                'destination_id': location['internalId']
            })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            location_attributes, self.workspace_id)
        return account_attributes

    def sync_departments(self):
        """
        Get departments
        """
        departments = self.connection.departments.get_all()

        department_attributes = []

        for department in departments:
            department_attributes.append({
                'attribute_type': 'DEPARTMENT',
                'display_name': 'Department',
                'value': department['name'],
                'destination_id': department['internalId']
            })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            department_attributes, self.workspace_id)
        return account_attributes

    def sync_vendors(self):
        """
        Get vendors
        """
        vendors = list(itertools.islice(self.connection.vendors.get_all_generator(), 10))

        vendor_attributes = []

        for vendor in vendors:
            vendor_attributes.append({
                'attribute_type': 'VENDOR',
                'display_name': 'Vendor',
                'value': vendor['entityId'],
                'destination_id': vendor['internalId']
            })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            vendor_attributes, self.workspace_id)
        return account_attributes

    def sync_subsidiaries(self):
        """
        Get subsidiaries
        """
        subsidiaries = self.connection.subsidiaries.get_all()

        subsidiary_attributes = []

        for subsidiary in subsidiaries:
            subsidiary_attributes.append({
                'attribute_type': 'SUBSIDIARY',
                'display_name': 'Subsidiary',
                'value': subsidiary['name'],
                'destination_id': subsidiary['internalId']
            })

        subsidiary_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            subsidiary_attributes, self.workspace_id)
        return subsidiary_attributes
