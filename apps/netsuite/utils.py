from typing import List, Dict

from netsuitesdk import NetSuiteConnection

from fyle_accounting_mappings.models import DestinationAttribute

from apps.fyle.models import Expense
from apps.fyle.utils import FyleConnector

from apps.mappings.models import SubsidiaryMapping
from apps.netsuite.models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem, JournalEntry, \
    JournalEntryLineItem, CustomSegment, VendorPayment, VendorPaymentLineitem
from apps.workspaces.models import NetSuiteCredentials, FyleCredential


def _decode_project_or_customer_name(name):
    value = name.replace(u'\xa0', ' ')
    value = value.replace('/', '-')

    return value


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
        Sync accounts
        """
        accounts = self.connection.accounts.get_all()

        account_attributes = []

        for account in accounts:
            if account['acctType'] != '_expense':
                account_attributes.append({
                    'attribute_type': 'BANK_ACCOUNT',
                    'display_name': 'Bank Account',
                    'value': account['acctName'],
                    'destination_id': account['internalId']
                })

                account_attributes.append({
                    'attribute_type': 'CREDIT_CARD_ACCOUNT',
                    'display_name': 'Credit Card Account',
                    'value': account['acctName'],
                    'destination_id': account['internalId']
                })

            if account['acctType'] == '_accountsPayable':
                account_attributes.append({
                    'attribute_type': 'ACCOUNTS_PAYABLE',
                    'display_name': 'Accounts Payable',
                    'value': account['acctName'],
                    'destination_id': account['internalId']
                })

            if account['acctType'] == '_expense':
                account_attributes.append({
                    'attribute_type': 'ACCOUNT',
                    'display_name': 'Account',
                    'value': account['acctName'],
                    'destination_id': account['internalId']
                })

                account_attributes.append({
                    'attribute_type': 'CCC_ACCOUNT',
                    'display_name': 'Credit Card Account',
                    'value': account['acctName'],
                    'destination_id': account['internalId']
                })

            if account['acctType'] == '_bank' or account['acctType'] == '_creditCard':
                account_attributes.append({
                    'attribute_type': 'VENDOR_PAYMENT_ACCOUNT',
                    'display_name': 'Vendor Payment Account',
                    'value': account['acctName'],
                    'destination_id': account['internalId']
                })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            account_attributes, self.workspace_id)
        return account_attributes

    def sync_expense_categories(self):
        """
        Sync Expense Categories
        """
        categories = self.connection.expense_categories.get_all()

        category_attributes = []

        for category in categories:
            category_attributes.append(
                {
                    'attribute_type': 'ACCOUNT',
                    'display_name': 'Expense Category',
                    'value': 'Expense Category - {}'.format(category['name']),
                    'destination_id': category['internalId']
                }
            )

            category_attributes.append(
                {
                    'attribute_type': 'CCC_ACCOUNT',
                    'display_name': 'Credit Card Expense Category',
                    'value': 'Expense Category - {}'.format(category['name']),
                    'destination_id': category['internalId']
                }
            )

        category_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            category_attributes, self.workspace_id)

        return category_attributes

    def sync_custom_segments(self, all_custom_list: List[CustomSegment]):
        """
        Sync Custom Segments
        """
        custom_segment_attributes = []

        for custom_list_values in all_custom_list:
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

        if custom_segment_attributes:
            custom_segment_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
                custom_segment_attributes, self.workspace_id)

        return custom_segment_attributes

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

        currency_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            currency_attributes, self.workspace_id)

        return currency_attributes

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

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            location_attributes, self.workspace_id)
        return account_attributes

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

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            classification_attributes, self.workspace_id)
        return account_attributes

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

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            department_attributes, self.workspace_id)
        return account_attributes

    def sync_vendors(self):
        """
        Sync vendors
        """
        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        vendors = self.connection.vendors.get_all()

        vendor_attributes = []

        for vendor in vendors:
            if 'subsidiary' in vendor and vendor['subsidiary']:
                if vendor['subsidiary']['internalId'] == subsidiary_mapping.internal_id:
                    vendor_attributes.append({
                        'attribute_type': 'VENDOR',
                        'display_name': 'Vendor',
                        'value': vendor['entityId'],
                        'destination_id': vendor['internalId']
                    })
            else:
                vendor_attributes.append({
                    'attribute_type': 'VENDOR',
                    'display_name': 'Vendor',
                    'value': vendor['entityId'],
                    'destination_id': vendor['internalId']
                })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            vendor_attributes, self.workspace_id)
        return account_attributes

    def sync_employees(self):
        """
        Sync employees
        """
        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        employees = self.connection.employees.get_all()

        employee_attributes = []

        for employee in employees:
            if 'subsidiary' in employee and employee['subsidiary']:
                if employee['subsidiary']['internalId'] == subsidiary_mapping.internal_id:
                    employee_attributes.append({
                        'attribute_type': 'EMPLOYEE',
                        'display_name': 'Employee',
                        'value': employee['entityId'],
                        'destination_id': employee['internalId']
                    })
            else:
                employee_attributes.append({
                    'attribute_type': 'EMPLOYEE',
                    'display_name': 'Employee',
                    'value': employee['entityId'],
                    'destination_id': employee['internalId']
                })

        account_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            employee_attributes, self.workspace_id)
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

    def sync_projects(self):
        """
        Sync projects
        """
        projects = self.connection.projects.get_all()

        project_attributes = []

        for project in projects:
            value = _decode_project_or_customer_name(project['entityId'])
            project_attributes.append({
                'attribute_type': 'PROJECT',
                'display_name': 'Project',
                'value': value,
                'destination_id': project['internalId'],
                'active': not project['isInactive']
            })

        project_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            project_attributes, self.workspace_id)
        return project_attributes

    def sync_customers(self):
        """
        Sync customers
        """
        customers = self.connection.customers.get_all()

        customers_attributes = []

        for customer in customers:
            value = _decode_project_or_customer_name(customer['entityId'])
            customers_attributes.append({
                'attribute_type': 'PROJECT',
                'display_name': 'Customer',
                'value': value,
                'destination_id': customer['internalId'],
                'active': not customer['isInactive']
            })

        customers_attributes = DestinationAttribute.bulk_upsert_destination_attributes(
            customers_attributes, self.workspace_id)
        return customers_attributes

    @staticmethod
    def __construct_bill_lineitems(bill_lineitems: List[BillLineitem],
                                   attachment_links: Dict, cluster_domain: str) -> List[Dict]:
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
                    'value': '{}/app/main/#/enterprise/view_expense/{}'.format(
                        cluster_domain,
                        expense.expense_id
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
                bill_lineitems, attachment_links, cluster_domain['cluster_domain']
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
    def __construct_expense_report_lineitems(
            expense_report_lineitems: List[ExpenseReportLineItem], attachment_links: Dict, cluster_domain: str
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
                    'value': '{}/app/main/#/enterprise/view_expense/{}'.format(
                        cluster_domain,
                        expense.expense_id
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
                'foreignAmount': None,
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
            'acctCorpCardExp': None,
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
                expense_report_lineitems, attachment_links, cluster_domain['cluster_domain']
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
    def __construct_journal_entry_lineitems(journal_entry_lineitems: List[JournalEntryLineItem],
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
                        'value': '{}/app/main/#/enterprise/view_expense/{}'.format(
                            cluster_domain,
                            expense.expense_id
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

        credit_line = self.__construct_journal_entry_lineitems(journal_entry_lineitems, credit='Credit')
        debit_line = self.__construct_journal_entry_lineitems(
            journal_entry_lineitems,
            debit='Debit', attachment_links=attachment_links, cluster_domain=cluster_domain['cluster_domain']
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
                'internalId': None,
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
                                   vendor_payment_lineitems: List[VendorPaymentLineitem]) -> Dict:
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
            'apAcct': None,
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
                'internalId': vendor_payment.department_id,
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
                            vendor_payment_lineitems: List[VendorPaymentLineitem]):
        """
        Post vendor payments to NetSuite
        """
        vendor_payment_payload = self.__construct_vendor_payment(vendor_payment, vendor_payment_lineitems)
        created_vendor_payment = self.connection.vendor_payments.post(vendor_payment_payload)
        return created_vendor_payment
