import json
from datetime import datetime
from typing import List, Dict
import logging

from requests_oauthlib import OAuth1Session

from netsuitesdk import NetSuiteConnection, NetSuiteRequestError

import unidecode

from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute

from apps.fyle.models import Expense, ExpenseGroup
from apps.fyle.connector import FyleConnector

from apps.mappings.models import SubsidiaryMapping
from apps.netsuite.models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem, JournalEntry, \
    JournalEntryLineItem, CustomSegment, VendorPayment, VendorPaymentLineitem, CreditCardChargeLineItem, \
    CreditCardCharge
from apps.workspaces.models import NetSuiteCredentials, FyleCredential, Workspace

logger = logging.getLogger(__name__)

SYNC_UPPER_LIMIT = {
    'projects': 5000,
    'customers': 5000
}


def _decode_project_or_customer_name(name):
    value = name.replace(u'\xa0', ' ')
    value = value.replace('/', '-')

    return value


class NetSuiteConnector:
    """
    NetSuite utility functions
    """

    def __init__(self, netsuite_credentials: NetSuiteCredentials, workspace_id: int,
                 search_body_fields_only: bool = True, page_size: int = 300):
        self.connection = NetSuiteConnection(
            account=netsuite_credentials.ns_account_id,
            consumer_key=netsuite_credentials.ns_consumer_key,
            consumer_secret=netsuite_credentials.ns_consumer_secret,
            token_key=netsuite_credentials.ns_token_id,
            token_secret=netsuite_credentials.ns_token_secret,
            search_body_fields_only=search_body_fields_only,
            page_size=page_size
        )

        self.__netsuite_credentials = netsuite_credentials

        self.workspace_id = workspace_id

    @staticmethod
    def __decode_project_or_customer_name(name):
        value = name.replace(u'\xa0', ' ')
        value = value.replace('/', '-')
        return value

    def sync_accounts(self):
        """
        Sync accounts
        """
        accounts_generator = self.connection.accounts.get_all_generator()
        for accounts in accounts_generator:
            attributes = {
                'bank_account': [],
                'credit_card_account': [],
                'accounts_payable': [],
                'account': [],
                'ccc_account': [],
                'vendor_payment_account': []
            }

            for account in list(accounts):
                if account['acctType'] != '_expense':
                    attributes['bank_account'].append({
                        'attribute_type': 'BANK_ACCOUNT',
                        'display_name': 'Bank Account',
                        'value': account['acctName'],
                        'destination_id': account['internalId']
                    })

                    attributes['credit_card_account'].append({
                        'attribute_type': 'CREDIT_CARD_ACCOUNT',
                        'display_name': 'Credit Card Account',
                        'value': account['acctName'],
                        'destination_id': account['internalId'],
                        'detail': {
                            'account_type': account['acctType']
                        }
                    })

                if account['acctType'] == '_accountsPayable':
                    attributes['accounts_payable'].append({
                        'attribute_type': 'ACCOUNTS_PAYABLE',
                        'display_name': 'Accounts Payable',
                        'value': account['acctName'],
                        'destination_id': account['internalId']
                    })

                if account['acctType'] == '_expense' or account['acctType'] == '_costOfGoodsSold' or \
                        account['acctType'] == '_otherCurrentAsset' or account['acctType'] == '_otherExpense':
                    attributes['account'].append({
                        'attribute_type': 'ACCOUNT',
                        'display_name': 'Account',
                        'value': unidecode.unidecode(u'{0}'.format(account['acctName'])).replace('/', '-'),
                        'destination_id': account['internalId']
                    })

                    attributes['ccc_account'].append({
                        'attribute_type': 'CCC_ACCOUNT',
                        'display_name': 'Credit Card Account',
                        'value': unidecode.unidecode(u'{0}'.format(account['acctName'])).replace('/', '-'),
                        'destination_id': account['internalId']
                    })

                if account['acctType'] == '_bank' or account['acctType'] == '_creditCard':
                    attributes['vendor_payment_account'].append({
                        'attribute_type': 'VENDOR_PAYMENT_ACCOUNT',
                        'display_name': 'Vendor Payment Account',
                        'value': account['acctName'],
                        'destination_id': account['internalId']
                    })

            for attribute_type, attribute in attributes.items():
                if attribute:
                    DestinationAttribute.bulk_create_or_update_destination_attributes(
                        attribute, attribute_type.upper(), self.workspace_id, True)

        return []

    def sync_expense_categories(self):
        """
        Sync Expense Categories
        """
        categories_generator = self.connection.expense_categories.get_all_generator()

        for categories in categories_generator:
            attributes = {
                'expense_category': [],
                'ccc_expense_category': []
            }
            for category in categories:
                detail = {
                    'account_name': category['expenseAcct']['name'],
                    'account_internal_id': category['expenseAcct']['internalId']
                }

                attributes['expense_category'].append(
                    {
                        'attribute_type': 'EXPENSE_CATEGORY',
                        'display_name': 'Expense Category',
                        'value': unidecode.unidecode(u'{0}'.format(category['name'])).replace('/', '-'),
                        'destination_id': category['internalId'],
                        'detail': detail
                    }
                )

                attributes['ccc_expense_category'].append(
                    {
                        'attribute_type': 'CCC_EXPENSE_CATEGORY',
                        'display_name': 'Credit Card Expense Category',
                        'value': unidecode.unidecode(u'{0}'.format(category['name'])).replace('/', '-'),
                        'destination_id': category['internalId'],
                        'detail': detail
                    }
                )

            for attribute_type, attribute in attributes.items():
                DestinationAttribute.bulk_create_or_update_destination_attributes(
                    attribute, attribute_type.upper(), self.workspace_id, True)

        return []

    def sync_custom_segments(self, all_custom_list: List[CustomSegment]):
        """
        Sync Custom Segments
        """
        for custom_list_values in all_custom_list:
            custom_segment_attributes = []

            if custom_list_values.segment_type == 'CUSTOM_LIST':
                custom_lists = self.connection.custom_lists.get(custom_list_values.internal_id)

                for field in custom_lists['customValueList']['customValue']:
                    custom_segment_attributes.append(
                        {
                            'attribute_type': custom_list_values.name.upper().replace(' ', '_'),
                            'display_name': custom_lists['name'],
                            'value': field['value'],
                            'destination_id': field['valueId']
                        }
                    )

            elif custom_list_values.segment_type == 'CUSTOM_RECORD':
                custom_records = self.connection.custom_records.get_all_by_id(custom_list_values.internal_id)

                for field in custom_records:
                    custom_segment_attributes.append(
                        {
                            'attribute_type': custom_list_values.name.upper().replace(' ', '_'),
                            'display_name': custom_records[0]['recType']['name'],
                            'value': field['name'],
                            'destination_id': field['internalId']
                        }
                    )

            DestinationAttribute.bulk_create_or_update_destination_attributes(custom_segment_attributes,
                                                                              custom_list_values.name.upper().replace(
                                                                                  ' ', '_'), self.workspace_id, True)

        return []

    def sync_currencies(self):
        """
        Sync Currencies
        """
        currencies = self.connection.currencies.get_all()

        currency_attributes = []

        for currency in currencies:
            currency_attributes.append(
                {
                    'attribute_type': 'CURRENCY',
                    'display_name': 'Currency',
                    'value': currency['symbol'],
                    'destination_id': currency['internalId']
                }
            )

        DestinationAttribute.bulk_create_or_update_destination_attributes(
            currency_attributes, 'CURRENCY', self.workspace_id, True)

        return []

    def sync_locations(self):
        """
        Sync locations
        """
        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        locations = self.connection.locations.get_all()

        location_attributes = []

        for location in locations:
            if 'subsidiaryList' in location and location['subsidiaryList']:
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
            else:
                location_attributes.append({
                    'attribute_type': 'LOCATION',
                    'display_name': 'Location',
                    'value': location['name'],
                    'destination_id': location['internalId']
                })

        DestinationAttribute.bulk_create_or_update_destination_attributes(location_attributes,
                                                                          'LOCATION', self.workspace_id, True)

        return []

    def sync_classifications(self):
        """
        Sync classification
        """
        classifications = self.connection.classifications.get_all()

        classification_attributes = []

        for classification in classifications:
            classification_attributes.append({
                'attribute_type': 'CLASS',
                'display_name': 'Class',
                'value': classification['name'],
                'destination_id': classification['internalId']
            })

        DestinationAttribute.bulk_create_or_update_destination_attributes(classification_attributes,
                                                                          'CLASS', self.workspace_id, True)

        return []

    def sync_departments(self):
        """
        Sync departments
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

        DestinationAttribute.bulk_create_or_update_destination_attributes(department_attributes,
                                                                          'DEPARTMENT', self.workspace_id, True)

        return []

    def sync_vendors(self):
        """
        Sync vendors
        """
        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        vendors_generator = self.connection.vendors.get_all_generator()

        for vendors in vendors_generator:
            attributes = []
            for vendor in vendors:
                detail = {
                    'email': vendor['email'] if vendor['email'] else None
                }
                if 'subsidiary' in vendor and vendor['subsidiary']:
                    if vendor['subsidiary']['internalId'] == subsidiary_mapping.internal_id:
                        attributes.append({
                            'attribute_type': 'VENDOR',
                            'display_name': 'Vendor',
                            'value': unidecode.unidecode(u'{0}'.format(vendor['entityId'])),
                            'destination_id': vendor['internalId'],
                            'detail': detail
                        })
                else:
                    attributes.append({
                        'attribute_type': 'VENDOR',
                        'display_name': 'Vendor',
                        'value': unidecode.unidecode(u'{0}'.format(vendor['entityId'])),
                        'destination_id': vendor['internalId'],
                        'detail': detail
                    })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                attributes, 'VENDOR', self.workspace_id, True)

        return []

    def post_vendor(self, expense_group: ExpenseGroup, vendor: ExpenseAttribute = None, merchant: str = None):
        """
        Create an Vendor on NetSuite
        :param expense_group: expense group
        :param vendor: vendor attribute to be created
        :param merchant: merchant to be created
        :return: Vendor Destination Attribute
        """
        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        expense = expense_group.expenses.first()

        currency = DestinationAttribute.objects.filter(value=expense.currency,
                                                       workspace_id=expense_group.workspace_id,
                                                       attribute_type='CURRENCY').first()

        netsuite_entity_id = vendor.detail['full_name'] if vendor else merchant

        vendor = {
            'firstName': netsuite_entity_id.split(' ')[0] if vendor else None,
            'lastName': (
                netsuite_entity_id.split(' ')[-1] if len(netsuite_entity_id.split(' ')) > 1 else netsuite_entity_id)
            if vendor else None,
            'isPerson': True if vendor else False,
            'entityId': netsuite_entity_id,
            'email': vendor.value if vendor else None,
            'companyName': merchant if merchant else None,
            'currency': {
                "name": None,
                "internalId": currency.destination_id if currency else '1',
                "externalId": None,
                "type": "currency"
            },
            'representingSubsidiary': {
                "name": None,
                "internalId": subsidiary_mapping.internal_id,
                "externalId": None,
                "type": None
            },
            'subsidiary': {
                'name': None,
                'internalId': subsidiary_mapping.internal_id,
                'externalId': None,
                'type': None
            },
            'workCalendar': {
                "name": None,
                "internalId": None,
                "externalId": None,
                "type": None
            },
            'externalId': vendor.detail['user_id'] if vendor else merchant
        }

        return self.connection.vendors.post(vendor)

    def sync_employees(self):
        """
        Sync employees
        """
        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        employees_generator = self.connection.employees.get_all_generator()

        for employees in employees_generator:
            attributes = []
            for employee in employees:
                detail = {
                    'email': employee['email'] if employee['email'] else None,
                    'department_id': employee['department']['internalId'] if employee['department'] else None
                }
                if 'subsidiary' in employee and employee['subsidiary']:
                    if employee['subsidiary']['internalId'] == subsidiary_mapping.internal_id:
                        attributes.append({
                            'attribute_type': 'EMPLOYEE',
                            'display_name': 'Employee',
                            'value': employee['entityId'],
                            'destination_id': employee['internalId'],
                            'detail': detail
                        })
                else:
                    attributes.append({
                        'attribute_type': 'EMPLOYEE',
                        'display_name': 'Employee',
                        'value': employee['entityId'],
                        'destination_id': employee['internalId'],
                        'detail': detail
                    })

            DestinationAttribute.bulk_create_or_update_destination_attributes(attributes,
                                                                              'EMPLOYEE', self.workspace_id, True)

        return []

    def create_destination_attribute(self, attribute: str, name: str, destination_id: str, email: str = None):
        created_attribute = DestinationAttribute.create_or_update_destination_attribute({
            'attribute_type': attribute.upper(),
            'display_name': attribute,
            'value': name,
            'destination_id': destination_id,
            'detail': {
                'email': email
            }
        }, self.workspace_id)

        return created_attribute

    def get_or_create_vendor(self, expense_attribute: ExpenseAttribute, expense_group: ExpenseGroup):
        vendor = self.connection.vendors.search(
            attribute='entityId', value=expense_attribute.detail['full_name'], operator='is')

        if not vendor:
            created_vendor = self.post_vendor(expense_group, expense_attribute)
            return self.create_destination_attribute(
                'vendor', expense_attribute.detail['full_name'], created_vendor['internalId'], expense_attribute.value)
        else:
            vendor = vendor[0]
            return self.create_destination_attribute(
                'vendor', vendor['entityId'], vendor['internalId'], vendor['email'])

    def get_or_create_employee(self, expense_attribute: ExpenseAttribute, expense_group: ExpenseGroup):
        employee = self.connection.employees.search(
            attribute='entityId', value=expense_attribute.detail['full_name'], operator='is'
        )

        if not employee:
            created_employee = self.post_employee(expense_attribute, expense_group)
            return self.create_destination_attribute(
                'employee', expense_attribute.detail['full_name'], created_employee['internalId'],
                expense_attribute.value
            )
        else:
            employee = employee[0]
            return self.create_destination_attribute(
                'employee', employee['entityId'], employee['internalId'], employee['email']
            )

    def sync_dimensions(self, workspace_id: str):
        try:
            self.sync_expense_categories()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_locations()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_vendors()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_currencies()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_classifications()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_departments()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_employees()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_accounts()
        except Exception as exception:
            logger.exception(exception)

        try:
            all_custom_list = CustomSegment.objects.filter(workspace_id=workspace_id).all()
            self.sync_custom_segments(all_custom_list)
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_projects()
        except Exception as exception:
            logger.exception(exception)

        try:
            self.sync_customers()
        except Exception as exception:
            logger.exception(exception)

    def post_employee(self, employee: ExpenseAttribute, expense_group: ExpenseGroup):
        """
        Create an Employee on NetSuite
        :param expense_group: expense group
        :param employee: employee attribute to be created
        :return: Employee Destination Attribute
        """
        department = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id, attribute_type='DEPARTMENT',
            value__iexact=employee.detail['department']).first()

        location = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id, attribute_type='LOCATION',
            value__iexact=employee.detail['location']).first()

        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        expense = expense_group.expenses.first()

        currency = DestinationAttribute.objects.filter(value=expense.currency,
                                                       workspace_id=self.workspace_id,
                                                       attribute_type='CURRENCY').first()

        employee_entity_id = employee.detail['full_name']

        employee = {
            'location': {
                'name': None,
                'internalId': location.destination_id if location else None,
                'externalId': None,
                'type': None
            },
            'department': {
                'name': None,
                'internalId': department.destination_id if department else None,
                'externalId': None,
                'type': None
            },
            'entityId': employee_entity_id,
            'email': employee.value,
            'firstName': employee_entity_id.split(' ')[0],
            'lastName': employee_entity_id.split(' ')[-1]
            if len(employee_entity_id.split(' ')) > 1 else '',
            'inheritIPRules': True,
            'payFrequency': None,
            'subsidiary': {
                'name': None,
                'internalId': subsidiary_mapping.internal_id,
                'externalId': None,
                'type': None
            },
            'workCalendar': {
                "name": None,
                "internalId": None,
                "externalId": None,
                "type": None
            },
            'defaultExpenseReportCurrency': {
                "internalId": currency.destination_id if currency else '1',
                "externalId": None,
                "type": "currency"
            },
            'externalId': employee.detail['user_id']
        }

        return self.connection.employees.post(employee)

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

        DestinationAttribute.bulk_create_or_update_destination_attributes(subsidiary_attributes,
                                                                          'SUBSIDIARY', self.workspace_id, True)

        return []

    def sync_projects(self):
        """
        Sync projects
        """
        projects_count = self.connection.projects.count()

        if projects_count <= SYNC_UPPER_LIMIT['projects']:
            projects_generator = self.connection.projects.get_all_generator()

            for projects in projects_generator:
                attributes = []
                for project in projects:
                    if not project['isInactive']:
                        value = _decode_project_or_customer_name(project['entityId'])
                        attributes.append({
                            'attribute_type': 'PROJECT',
                            'display_name': 'Project',
                            'value': value,
                            'destination_id': project['internalId'],
                            'active': True
                        })
                DestinationAttribute.bulk_create_or_update_destination_attributes(
                    attributes, 'PROJECT', self.workspace_id, True)

        return []

    def sync_customers(self):
        """
        Sync customers
        """
        customers_count = self.connection.customers.count()

        if customers_count <= SYNC_UPPER_LIMIT['customers']:
            customers_generator = self.connection.customers.get_all_generator()

            for customers in customers_generator:
                attributes = []
                for customer in customers:
                    if not customer['isInactive']:
                        value = _decode_project_or_customer_name(customer['entityId'])
                        attributes.append({
                            'attribute_type': 'PROJECT',
                            'display_name': 'Customer',
                            'value': value,
                            'destination_id': customer['internalId'],
                            'active': True
                        })

                DestinationAttribute.bulk_create_or_update_destination_attributes(
                    attributes, 'PROJECT', self.workspace_id, True)

        return []

    @staticmethod
    def __construct_bill_lineitems(bill_lineitems: List[BillLineitem],
                                   attachment_links: Dict, cluster_domain: str, org_id: str) -> List[Dict]:
        """
        Create bill line items
        :return: constructed line items
        """
        lines = []

        for line in bill_lineitems:
            expense = Expense.objects.get(pk=line.expense_id)

            netsuite_custom_segments = line.netsuite_custom_segments

            if attachment_links and expense.expense_id in attachment_links:
                netsuite_custom_segments.append(
                    {
                        'scriptId': 'custcolfyle_receipt_link',
                        'type': 'String',
                        'value': attachment_links[expense.expense_id]
                    }
                )

            netsuite_custom_segments.append(
                {
                    'scriptId': 'custcolfyle_expense_url',
                    'type': 'String',
                    'value': '{}/app/main/#/enterprise/view_expense/{}?org_id={}'.format(
                        cluster_domain,
                        expense.expense_id,
                        org_id
                    )
                }
            )

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
                    'name': None,
                    'internalId': line.location_id,
                    'externalId': None,
                    'type': 'location'
                },
                'customer': {
                    'name': None,
                    'internalId': line.customer_id,
                    'externalId': None,
                    'type': 'customer'
                },
                'customFieldList': netsuite_custom_segments,
                'isBillable': line.billable,
                'projectTask': None,
                'taxCode': None,
                'taxRate1': None,
                'taxRate2': None,
                'amortizationSched': None,
                'amortizStartDate': None,
                'amortizationEndDate': None,
                'amortizationResidual': None,
            }
            lines.append(line)

        return lines

    def __construct_bill(self, bill: Bill, bill_lineitems: List[BillLineitem], attachment_links: Dict) -> Dict:
        """
        Create a bill
        :return: constructed bill
        """

        fyle_credentials = FyleCredential.objects.get(workspace_id=bill.expense_group.workspace_id)
        fyle_connector = FyleConnector(fyle_credentials.refresh_token, bill.expense_group.workspace_id)

        cluster_domain = fyle_connector.get_cluster_domain()
        org_id = Workspace.objects.get(id=bill.expense_group.workspace_id).fyle_org_id

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
                'internalId': bill.entity_id,
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
                'name': None,
                'internalId': bill.location_id,
                'externalId': None,
                'type': 'location'
            },
            'approvalStatus': None,
            'nextApprover': None,
            'vatRegNum': None,
            'postingPeriod': None,
            'tranDate': bill.transaction_date,
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
                'name': None,
                'internalId': bill.currency,
                'externalId': None,
                'type': 'currency'
            },
            'status': None,
            'landedCostMethod': None,
            'landedCostPerLine': None,
            'transactionNumber': None,
            'expenseList': self.__construct_bill_lineitems(
                bill_lineitems, attachment_links, cluster_domain['cluster_domain'], org_id
            ),
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

    def post_bill(self, bill: Bill, bill_lineitems: List[BillLineitem], attachment_links: Dict):
        """
        Post vendor bills to NetSuite
        """
        bills_payload = self.__construct_bill(bill, bill_lineitems, attachment_links)
        created_bill = self.connection.vendor_bills.post(bills_payload)
        return created_bill

    def get_bill(self, internal_id):
        """
        GET vendor bill from NetSuite
        """
        bill = self.connection.vendor_bills.get(internal_id)
        return bill

    @staticmethod
    def __construct_credit_card_charge_lineitems(
            credit_card_charge_lineitem: CreditCardChargeLineItem,
            attachment_links: Dict, cluster_domain: str, org_id: str) -> List[Dict]:
        """
        Create credit_card_charge line items
        :return: constructed line items
        """
        line = credit_card_charge_lineitem

        lines = []

        expense = Expense.objects.get(pk=line.expense_id)

        netsuite_custom_segments = line.netsuite_custom_segments

        if attachment_links and expense.expense_id in attachment_links:
            netsuite_custom_segments.append(
                {
                    'scriptId': 'custcolfyle_receipt_link',
                    'value': attachment_links[expense.expense_id]
                }
            )

        netsuite_custom_segments.append(
            {
                'scriptId': 'custcolfyle_expense_url',
                'value': '{}/app/main/#/enterprise/view_expense/{}?org_id={}'.format(
                    cluster_domain,
                    expense.expense_id,
                    org_id
                )
            }
        )

        line = {
            'account': {
                'internalId': line.account_id
            },
            'amount': line.amount,
            'memo': line.memo,
            'department': {
                'internalId': line.department_id
            },
            'class': {
                'internalId': line.class_id
            },
            'location': {
                'internalId': line.location_id
            },
            'customer': {
                'internalId': line.customer_id
            },
            'customFieldList': netsuite_custom_segments,
            'isBillable': line.billable,
        }
        lines.append(line)

        return lines

    def __construct_credit_card_charge(
            self, credit_card_charge: CreditCardCharge,
            credit_card_charge_lineitem: CreditCardChargeLineItem, attachment_links: Dict) -> Dict:
        """
        Create a credit_card_charge
        :return: constructed credit_card_charge
        """

        fyle_credentials = FyleCredential.objects.get(workspace_id=credit_card_charge.expense_group.workspace_id)
        fyle_connector = FyleConnector(fyle_credentials.refresh_token, credit_card_charge.expense_group.workspace_id)

        cluster_domain = fyle_connector.get_cluster_domain()
        org_id = Workspace.objects.get(id=credit_card_charge.expense_group.workspace_id).fyle_org_id

        transaction_date = datetime.strptime(credit_card_charge.transaction_date, '%Y-%m-%d').strftime('%m/%d/%Y')

        credit_card_charge_payload = {
            'account': {
                'internalId': credit_card_charge.credit_card_account_id
            },
            'entity': {
                'internalId': credit_card_charge.entity_id
            },
            'subsidiary': {
                'internalId': credit_card_charge.subsidiary_id
            },
            'location': {
                'internalId': credit_card_charge.location_id
            },
            'currency': {
                'internalId': credit_card_charge.currency
            },
            'tranDate': transaction_date,
            'memo': credit_card_charge.memo,
            'expenses': self.__construct_credit_card_charge_lineitems(
                credit_card_charge_lineitem, attachment_links, cluster_domain['cluster_domain'], org_id
            ),
            'externalId': credit_card_charge.external_id
        }

        return credit_card_charge_payload

    def post_credit_card_charge(self, credit_card_charge: CreditCardCharge,
                                credit_card_charge_lineitem: CreditCardChargeLineItem, attachment_links: Dict):
        """
        Post vendor credit_card_charges to NetSuite
        """
        credit_card_charges_payload = self.__construct_credit_card_charge(
            credit_card_charge, credit_card_charge_lineitem, attachment_links)

        account = self.__netsuite_credentials.ns_account_id.replace('_', '-')
        consumer_key = self.__netsuite_credentials.ns_consumer_key
        consumer_secret = self.__netsuite_credentials.ns_consumer_secret
        token_key = self.__netsuite_credentials.ns_token_id
        token_secret = self.__netsuite_credentials.ns_token_secret

        url = f"https://{account.lower()}.restlets.api.netsuite.com/app/site/hosting/restlet.nl?" \
              f"script=customscript_cc_charge_fyle&deploy=customdeploy_cc_charge_fyle"

        oauth = OAuth1Session(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=token_key,
            resource_owner_secret=token_secret,
            realm=account,
            signature_method='HMAC-SHA256'
        )

        raw_response = oauth.post(
            url, headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }, data=json.dumps(credit_card_charges_payload))

        status_code = raw_response.status_code

        if status_code == 200 and 'success' in json.loads(raw_response.text) \
                and json.loads(raw_response.text)['success']:
            return json.loads(raw_response.text)

        response = eval(raw_response.text)

        code = response['error']['code']
        message = json.loads(response['error']['message'])['message']

        raise NetSuiteRequestError(code=code, message=message)

    @staticmethod
    def __construct_expense_report_lineitems(
            expense_report_lineitems: List[ExpenseReportLineItem], attachment_links: Dict, cluster_domain: str,
            org_id: str
    ) -> List[Dict]:
        """
        Create expense report line items
        :return: constructed line items
        """
        lines = []

        for line in expense_report_lineitems:
            expense = Expense.objects.get(pk=line.expense_id)

            netsuite_custom_segments = line.netsuite_custom_segments
            if attachment_links and expense.expense_id in attachment_links:
                netsuite_custom_segments.append(
                    {
                        'scriptId': 'custcolfyle_receipt_link',
                        'type': 'String',
                        'value': attachment_links[expense.expense_id]
                    }
                )

            netsuite_custom_segments.append(
                {
                    'scriptId': 'custcolfyle_expense_url',
                    'type': 'String',
                    'value': '{}/app/main/#/enterprise/view_expense/{}?org_id={}'.format(
                        cluster_domain,
                        expense.expense_id,
                        org_id
                    )
                }
            )

            line = {
                'amount': line.amount,
                'category': {
                    'name': None,
                    'internalId': line.category,
                    'externalId': None,
                    'type': 'account'
                },
                'corporateCreditCard': True if expense.fund_source == 'CCC' else None,
                'currency': {
                    'name': None,
                    'internalId': line.currency,
                    'externalId': None,
                    'type': 'currency'
                },
                'customer': {
                    'name': None,
                    'internalId': line.customer_id,
                    'externalId': None,
                    'type': 'customer'
                },
                'location': {
                    'name': None,
                    'internalId': line.location_id,
                    'externalId': None,
                    'type': 'location'
                },
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
                'customFieldList': netsuite_custom_segments,
                'exchangeRate': None,
                'expenseDate': line.transaction_date,
                'expMediaItem': None,
                'foreignAmount': expense.foreign_amount if expense.foreign_amount else None,
                'grossAmt': None,
                'isBillable': line.billable,
                'isNonReimbursable': None,
                'line': None,
                'memo': line.memo,
                'quantity': None,
                'rate': None,
                'receipt': None,
                'refNumber': None,
                'tax1Amt': None,
                'taxCode': None,
                'taxRate1': None,
                'taxRate2': None
            }

            lines.append(line)

        return lines

    def __construct_expense_report(self, expense_report: ExpenseReport,
                                   expense_report_lineitems: List[ExpenseReportLineItem],
                                   attachment_links: Dict) -> Dict:
        """
        Create a expense report
        :return: constructed expense report
        """

        fyle_credentials = FyleCredential.objects.get(workspace_id=expense_report.expense_group.workspace_id)
        fyle_connector = FyleConnector(fyle_credentials.refresh_token, expense_report.expense_group.workspace_id)

        cluster_domain = fyle_connector.get_cluster_domain()
        org_id = Workspace.objects.get(id=expense_report.expense_group.workspace_id).fyle_org_id

        expense_report_payload = {
            'nullFieldList': None,
            'createdDate': None,
            'lastModifiedDate': None,
            'status': None,
            'customForm': None,
            'account': {
                'name': None,
                'internalId': expense_report.account_id,
                'externalId': None,
                'type': 'account'
            },
            'entity': {
                'name': None,
                'internalId': expense_report.entity_id,
                'externalId': None,
                'type': 'vendor'
            },
            'expenseReportCurrency': {
                'name': None,
                'internalId': expense_report.currency,
                'externalId': None,
                'type': 'currency'
            },
            'subsidiary': {
                'name': None,
                'internalId': expense_report.subsidiary_id,
                'externalId': None,
                'type': 'subsidiary'
            },
            'expenseReportExchangeRate': None,
            'taxPointDate': None,
            'tranId': None,
            'acctCorpCardExp': {
                'name': None,
                'internalId': expense_report.credit_card_account_id,
                'externalId': None,
                'type': 'account'
            },
            'postingPeriod': None,
            'tranDate': expense_report.transaction_date,
            'dueDate': None,
            'approvalStatus': None,
            'total': None,
            'nextApprover': None,
            'advance': None,
            'tax1Amt': None,
            'amount': None,
            'memo': expense_report.memo,
            'complete': None,
            'supervisorApproval': True,
            'accountingApproval': True,
            'useMultiCurrency': None,
            'tax2Amt': None,
            'department': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'department'
            },
            'class': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'classification'
            },
            'location': {
                'name': None,
                'internalId': expense_report.location_id,
                'externalId': None,
                'type': 'location'
            },
            'expenseList': self.__construct_expense_report_lineitems(
                expense_report_lineitems, attachment_links, cluster_domain['cluster_domain'], org_id
            ),
            'accountingBookDetailList': None,
            'customFieldList': None,
            'internalId': None,
            'externalId': expense_report.external_id
        }

        return expense_report_payload

    def post_expense_report(
            self, expense_report: ExpenseReport,
            expense_report_lineitems: List[ExpenseReportLineItem], attachment_links: Dict):
        """
        Post expense reports to NetSuite
        """
        expense_report_payload = self.__construct_expense_report(expense_report,
                                                                 expense_report_lineitems, attachment_links)
        created_expense_report = self.connection.expense_reports.post(expense_report_payload)
        return created_expense_report

    def get_expense_report(self, internal_id):
        """
        GET expense report from NetSuite
        """
        expense_report = self.connection.expense_reports.get(internal_id)
        return expense_report

    @staticmethod
    def __construct_journal_entry_lineitems(journal_entry_lineitems: List[JournalEntryLineItem], org_id: str,
                                            credit=None, debit=None, attachment_links: Dict = None,
                                            cluster_domain: str = None) -> List[Dict]:
        """
        Create journal entry line items
        :return: constructed line items
        """
        lines = []

        for line in journal_entry_lineitems:
            expense = Expense.objects.get(pk=line.expense_id)
            account_ref = None
            if credit is None:
                account_ref = line.account_id

            if debit is None:
                account_ref = line.debit_account_id

            netsuite_custom_segments = line.netsuite_custom_segments

            if attachment_links and expense.expense_id in attachment_links:
                netsuite_custom_segments.append(
                    {
                        'scriptId': 'custcolfyle_receipt_link',
                        'type': 'String',
                        'value': attachment_links[expense.expense_id]
                    }
                )

            if debit:
                netsuite_custom_segments.append(
                    {
                        'scriptId': 'custcolfyle_expense_url',
                        'type': 'String',
                        'value': '{}/app/main/#/enterprise/view_expense/{}?org_id={}'.format(
                            cluster_domain,
                            expense.expense_id,
                            org_id
                        )
                    }
                )

            line = {
                'account': {
                    'name': None,
                    'internalId': account_ref,
                    'externalId': None,
                    'type': 'account'
                },
                'department': {
                    'name': None,
                    'internalId': line.department_id,
                    'externalId': None,
                    'type': 'department'
                },
                'location': {
                    'name': None,
                    'internalId': line.location_id,
                    'externalId': None,
                    'type': 'location'
                },
                'class': {
                    'name': None,
                    'internalId': line.class_id,
                    'externalId': None,
                    'type': 'classification'
                },
                'entity': {
                    'name': None,
                    'internalId': line.entity_id,
                    'externalId': None,
                    'type': 'vendor'
                },
                'credit': line.amount if credit is not None else None,
                'creditTax': None,
                'customFieldList': netsuite_custom_segments,
                'debit': line.amount if debit is not None else None,
                'debitTax': None,
                'eliminate': None,
                'endDate': None,
                'grossAmt': None,
                'line': None,
                'lineTaxCode': None,
                'lineTaxRate': None,
                'memo': line.memo,
                'residual': None,
                'revenueRecognitionRule': None,
                'schedule': None,
                'scheduleNum': None,
                'startDate': None,
                'tax1Acct': None,
                'tax1Amt': None,
                'taxAccount': None,
                'taxBasis': None,
                'taxCode': None,
                'taxRate1': None,
                'totalAmount': None,
            }

            lines.append(line)

        return lines

    def __construct_journal_entry(self, journal_entry: JournalEntry,
                                  journal_entry_lineitems: List[JournalEntryLineItem],
                                  attachment_links: Dict) -> Dict:
        """
        Create a journal entry report
        :return: constructed journal entry
        """
        fyle_credentials = FyleCredential.objects.get(workspace_id=journal_entry.expense_group.workspace_id)
        fyle_connector = FyleConnector(fyle_credentials.refresh_token, journal_entry.expense_group.workspace_id)

        cluster_domain = fyle_connector.get_cluster_domain()
        org_id = Workspace.objects.get(id=journal_entry.expense_group.workspace_id).fyle_org_id

        credit_line = self.__construct_journal_entry_lineitems(journal_entry_lineitems, credit='Credit', org_id=org_id)
        debit_line = self.__construct_journal_entry_lineitems(
            journal_entry_lineitems,
            debit='Debit', attachment_links=attachment_links,
            cluster_domain=cluster_domain['cluster_domain'], org_id=org_id
        )
        lines = []
        lines.extend(credit_line)
        lines.extend(debit_line)

        journal_entry_payload = {
            'accountingBook': None,
            'accountingBookDetailList': None,
            'approved': None,
            'createdDate': None,
            'createdFrom': None,
            'currency': {
                'name': None,
                'internalId': journal_entry.currency,
                'externalId': None,
                'type': 'currency'
            },
            'customFieldList': None,
            'customForm': None,
            'class': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'classification'
            },
            'department': {
                'name': None,
                'internalId': journal_entry.department_id,
                'externalId': None,
                'type': 'department'
            },
            'location': {
                'name': None,
                'internalId': journal_entry.location_id,
                'externalId': None,
                'type': 'location'
            },
            'exchangeRate': None,
            'isBookSpecific': None,
            'lastModifiedDate': None,
            'lineList': lines,
            'memo': journal_entry.memo,
            'nexus': None,
            'parentExpenseAlloc': None,
            'postingPeriod': None,
            'reversalDate': None,
            'reversalDefer': None,
            'reversalEntry': None,
            'subsidiary': {
                'name': None,
                'internalId': journal_entry.subsidiary_id,
                'externalId': None,
                'type': 'subsidiary'
            },
            'subsidiaryTaxRegNum': None,
            'taxPointDate': None,
            'toSubsidiary': None,
            'tranDate': journal_entry.transaction_date,
            'tranId': None,
            'externalId': journal_entry.external_id
        }

        return journal_entry_payload

    def post_journal_entry(self, journal_entry: JournalEntry,
                           journal_entry_lineitems: List[JournalEntryLineItem], attachment_links: Dict):
        """
        Post journal entries to NetSuite
        """
        journal_entry_payload = self.__construct_journal_entry(journal_entry, journal_entry_lineitems, attachment_links)
        created_journal_entry = self.connection.journal_entries.post(journal_entry_payload)
        return created_journal_entry

    @staticmethod
    def __construct_vendor_payment_lineitems(vendor_payment_lineitems: List[VendorPaymentLineitem]) -> List[Dict]:
        """
        Create vendor payment line items
        :return: constructed line items
        """
        lines = []

        for line in vendor_payment_lineitems:
            line = {
                'apply': 'true',
                'doc': line.doc_id,
                'line': 0,
                'job': None,
                'applyDate': None,
                'type': None,
                'refNum': None,
                'total': None,
                'due': None,
                'currency': None,
                'discDate': None,
                'discAmt': None,
                'disc': None,
                'amount': None
            }

            lines.append(line)

        return lines

    def __construct_vendor_payment(self, vendor_payment: VendorPayment,
                                   vendor_payment_lineitems: List[VendorPaymentLineitem],
                                   department) -> Dict:
        """
        Create a vendor payment
        :return: constructed vendor payment
        """
        vendor_payment_payload = {
            'nullFieldList': None,
            'createdDate': None,
            'lastModifiedDate': None,
            'customForm': None,
            'account': {
                'name': None,
                'internalId': vendor_payment.account_id,
                'externalId': None,
                'type': None
            },
            'balance': None,
            'apAcct': {
                'name': None,
                'internalId': vendor_payment.accounts_payable_id,
                'externalId': None,
                'type': None
            },
            'entity': {
                'name': None,
                'internalId': vendor_payment.entity_id,
                'externalId': None,
                'type': None
            },
            'address': None,
            'tranDate': None,
            'voidJournal': None,
            'postingPeriod': None,
            'currencyName': None,
            'exchangeRate': None,
            'toAch': 'false',
            'toBePrinted': 'false',
            'printVoucher': 'false',
            'tranId': None,
            'total': None,
            'currency': {
                'name': None,
                'internalId': vendor_payment.currency,
                'externalId': None,
                'type': None
            },
            'department': {
                'name': None,
                'internalId': department['internalId'] if (department and 'internalId' in department) else None,
                'externalId': None,
                'type': 'department'
            },
            'memo': vendor_payment.memo,
            'subsidiary': {
                'name': None,
                'internalId': vendor_payment.subsidiary_id,
                'externalId': None,
                'type': None
            },
            'class': {
                'name': None,
                'internalId': vendor_payment.class_id,
                'externalId': None,
                'type': 'classification'
            },
            'location': {
                'name': None,
                'internalId': vendor_payment.location_id,
                'externalId': None,
                'type': 'location'
            },
            'status': None,
            'transactionNumber': None,
            'applyList': {
                'apply':
                    self.__construct_vendor_payment_lineitems(vendor_payment_lineitems),
                'replaceAll': 'true'
            },
            'creditList': None,
            'billPay': None,
            'accountingBookDetailList': None,
            'availableBalance': None,
            'isInTransitPayment': None,
            'approvalStatus': None,
            'nextApprover': None,
            'customFieldList': None,
            'internalId': None,
            'externalId': vendor_payment.external_id
        }

        return vendor_payment_payload

    def post_vendor_payment(self, vendor_payment: VendorPayment,
                            vendor_payment_lineitems: List[VendorPaymentLineitem],
                            first_object):
        """
        Post vendor payments to NetSuite
        """
        department = first_object['department']

        vendor_payment_payload = self.__construct_vendor_payment(
            vendor_payment, vendor_payment_lineitems, department
        )
        created_vendor_payment = self.connection.vendor_payments.post(vendor_payment_payload)
        return created_vendor_payment
