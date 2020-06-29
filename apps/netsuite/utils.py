import itertools
from typing import List, Dict

from netsuitesdk import NetSuiteConnection
from fyle_accounting_mappings.models import DestinationAttribute

from apps.mappings.models import SubsidiaryMapping
from apps.netsuite.models import Bill, BillLineitem
from apps.workspaces.models import NetSuiteCredentials


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

        self.queryset = SubsidiaryMapping.objects.all()

    def sync_accounts(self, account_type):
        """
        Sync accounts
        """
        accounts = self.connection.accounts.get_all()

        accounts = list(filter(lambda current_account: current_account['acctType'] == account_type, accounts))

        account_attributes = []

        if account_type == '_expense':
            attribute_type = 'ACCOUNT'
            display_name = 'Account'
        elif account_type == '_accountsPayable':
            attribute_type = 'ACCOUNTS_PAYABLE'
            display_name = 'Accounts Payable'
        else:
            attribute_type = None
            display_name = None

        for account in accounts:
            account_attributes.append({
                'attribute_type': attribute_type,
                'display_name': display_name,
                'value': account['acctName'],
                'destination_id': account['internalId']
            })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            account_attributes, self.workspace_id)
        return account_attributes

    def sync_locations(self):
        """
        Sync locations
        """
        subsidiary_mapping = self.queryset.get(workspace_id=self.workspace_id)

        locations = self.connection.locations.get_all()

        location_attributes = []

        for location in locations:
            subsidiaries = location['subsidiaryList']['recordRef']
            counter = 0
            if subsidiaries[counter]['internalId'] == subsidiary_mapping.internal_id:
                counter += 1
                location_attributes.append({
                    'attribute_type': 'LOCATION',
                    'display_name': 'Location',
                    'value': location['name'],
                    'destination_id': location['internalId']
                })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            location_attributes, self.workspace_id)
        return account_attributes

    def sync_classifications(self):
        """
        Sync classification
        """
        subsidiary_mapping = self.queryset.get(workspace_id=self.workspace_id)

        classifications = self.connection.classifications.get_all()

        classification_attributes = []

        for classification in classifications:
            subsidiaries = classification['subsidiaryList']['recordRef']
            counter = 0
            if subsidiaries[counter]['internalId'] == subsidiary_mapping.internal_id:
                counter += 1
                classification_attributes.append({
                    'attribute_type': 'CLASS',
                    'display_name': 'Class',
                    'value': classification['name'],
                    'destination_id': classification['internalId']
                })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            classification_attributes, self.workspace_id)
        return account_attributes

    def sync_departments(self):
        """
        Sync departments
        """
        subsidiary_mapping = self.queryset.get(workspace_id=self.workspace_id)

        departments = self.connection.departments.get_all()

        department_attributes = []

        for department in departments:
            subsidiaries = department['subsidiaryList']['recordRef']
            counter = 0
            if subsidiaries[counter]['internalId'] == subsidiary_mapping.internal_id:
                counter += 1
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
        Sync vendors
        """
        subsidiary_mapping = self.queryset.get(workspace_id=self.workspace_id)

        vendors = list(itertools.islice(self.connection.vendors.get_all_generator(), 10))

        vendor_attributes = []

        for vendor in vendors:
            if vendor['subsidiary']['internalId'] == subsidiary_mapping.internal_id:
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
        Sync subsidiaries
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

    @staticmethod
    def __construct_bill_lineitems(bill_lineitems: List[BillLineitem]) -> List[Dict]:
        """
        Create bill line items
        :return: constructed line items
        """
        lines = []

        for line in bill_lineitems:
            line = {
                'orderDoc': None,
                'orderLine': None,
                'line': None,
                'category': None,
                'account': {
                    'name': None,
                    'internalId': line.account_id,
                    'externalId': None,
                    'type': 'account'
                },
                'amount': line.amount,
                'taxAmount': None,
                'tax1Amt': None,
                'memo': line.memo,
                'grossAmt': None,
                'taxDetailsReference': None,
                'department': {
                    'name': None,
                    'internalId': line.department_id,
                    'externalId': None,
                    'type': 'department'
                },
                'class': {
                    'name': None,
                    'internalId': line.class_id,
                    'externalId': None,
                    'type': 'classification'
                },
                'location': {
                    "name": None,
                    "internalId": line.location_id,
                    'externalId': None,
                    'type': 'location'
                },

                'customer': None,
                'isBillable': None,
                'projectTask': None,
                'taxCode': None,
                'taxRate1': None,
                'taxRate2': None,
                'amortizationSched': None,
                'amortizStartDate': None,
                'amortizationEndDate': None,
                'amortizationResidual': None,
                'customFieldList': None
            }
            lines.append(line)

        return lines

    def __construct_bill(self, bill: Bill, bill_lineitems: List[BillLineitem]) -> Dict:
        """
        Create a bill
        :return: constructed bill
        """

        bill_payload = {
            'nullFieldList': None,
            'createdDate': None,
            'lastModifiedDate': None,
            'nexus': None,
            'subsidiaryTaxRegNum': None,
            'taxRegOverride': None,
            'taxDetailsOverride': None,
            'customForm': None,
            'billAddressList': None,
            'account': {
                'name': None,
                'internalId': bill.accounts_payable_id,
                'externalId': None,
                'type': 'account'
            },
            'entity': {
                'name': None,
                'internalId': bill.vendor_id,
                'externalId': None,
                'type': 'vendor'
            },
            'subsidiary': {
                'name': None,
                'internalId': bill.subsidiary_id,
                'externalId': None,
                'type': 'subsidiary'
            },
            'location': {
                "name": None,
                "internalId": bill.location_id,
                'externalId': None,
                'type': 'location'
            },
            'approvalStatus': None,
            'nextApprover': None,
            'vatRegNum': None,
            'postingPeriod': None,
            'tranDate': None,
            'currencyName': None,
            'billingAddress': None,
            'exchangeRate': None,
            'entityTaxRegNum': None,
            'taxPointDate': None,
            'terms': None,
            'dueDate': None,
            'discountDate': None,
            'tranId': None,
            'userTotal': None,
            'discountAmount': None,
            'taxTotal': None,
            'paymentHold': None,
            'memo': bill.memo,
            'tax2Total': None,
            'creditLimit': None,
            'availableVendorCredit': None,
            'currency': {
                'name': bill.currency,
                'internalId': None,
                'externalId': None,
                'type': 'currency'
            },
            'status': None,
            'landedCostMethod': None,
            'landedCostPerLine': None,
            'transactionNumber': None,
            'expenseList': self.__construct_bill_lineitems(bill_lineitems),
            'accountingBookDetailList': None,
            'itemList': None,
            'landedCostsList': None,
            'purchaseOrderList': None,
            'taxDetailsList': None,
            'customFieldList': None,
            'internalId': None,
            'externalId': bill.external_id
        }

        return bill_payload

    def post_bill(self, bill: Bill, bill_lineitems: List[BillLineitem]):
        """
        Post vendor bills to NetSuite
        """
        bills_payload = self.__construct_bill(bill, bill_lineitems)
        created_bill = self.connection.vendor_bills.post(bills_payload)
        return created_bill
