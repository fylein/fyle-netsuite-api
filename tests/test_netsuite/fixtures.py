from datetime import datetime

data = {
    "vendor": [
        {
            "nullFieldList": None,
            "customForm": None,
            "entityId": "Uber BV",
            "altName": None,
            "isPerson": False,
            "phoneticName": None,
            "salutation": None,
            "firstName": None,
            "middleName": None,
            "lastName": None,
            "companyName": "Uber BV",
            "phone": None,
            "fax": None,
            "email": None,
            "url": None,
            "defaultAddress": None,
            "isInactive": False,
            "category": None,
            "title": None,
            "printOnCheckAs": None,
            "altPhone": None,
            "homePhone": None,
            "mobilePhone": None,
            "altEmail": None,
            "comments": None,
            "globalSubscriptionStatus": None,
            "image": None,
            "emailPreference": None,
            "subsidiary": {
                "name": "HoneComb Aus",
                "internalId": "5",
                "externalId": None,
                "type": None,
            },
            "representingSubsidiary": None,
            "accountNumber": None,
            "legalName": "Uber BV",
            "vatRegNumber": None,
            "expenseAccount": None,
            "payablesAccount": None,
            "terms": None,
            "incoterm": None,
            "creditLimit": None,
            "balancePrimary": None,
            "openingBalance": None,
            "openingBalanceDate": None,
            "openingBalanceAccount": None,
            "balance": None,
            "unbilledOrdersPrimary": None,
            "bcn": None,
            "unbilledOrders": None,
            "currency": {
                "name": "USA",
                "internalId": "1",
                "externalId": None,
                "type": None,
            },
            "is1099Eligible": False,
            "isJobResourceVend": False,
            "laborCost": None,
            "purchaseOrderQuantity": None,
            "purchaseOrderAmount": None,
            "purchaseOrderQuantityDiff": None,
            "receiptQuantity": None,
            "receiptAmount": None,
            "receiptQuantityDiff": None,
            "workCalendar": {
                "name": "Default Work Calendar",
                "internalId": "1",
                "externalId": None,
                "type": None,
            },
            "taxIdNum": None,
            "taxItem": None,
            "giveAccess": False,
            "sendEmail": None,
            "billPay": False,
            "isAccountant": None,
            "password": None,
            "password2": None,
            "requirePwdChange": None,
            "eligibleForCommission": None,
            "emailTransactions": None,
            "printTransactions": None,
            "faxTransactions": None,
            "defaultTaxReg": None,
            "pricingScheduleList": None,
            "subscriptionsList": None,
            "addressbookList": None,
            "currencyList": None,
            "rolesList": None,
            "taxRegistrationList": None,
            "customFieldList": {
                "customField": [
                    {
                        "value": False,
                        "internalId": "3992",
                        "scriptId": "custentity_2663_payment_method",
                    },
                    {
                        "value": False,
                        "internalId": "35",
                        "scriptId": "custentity_is_manufacturer",
                    },
                ]
            },
            "internalId": "12106",
            "externalId": "Uber BV",
        }
    ],
    "bill_payload": [
        {
            "nullFieldList": None,
            "createdDate": None,
            "lastModifiedDate": None,
            "nexus": None,
            "subsidiaryTaxRegNum": None,
            "taxRegOverride": None,
            "taxDetailsOverride": None,
            "customForm": None,
            "billAddressList": None,
            "account": {
                "name": None,
                "internalId": "25",
                "externalId": None,
                "type": "account",
            },
            "entity": {
                "name": None,
                "internalId": "10693",
                "externalId": None,
                "type": "vendor",
            },
            "subsidiary": {
                "name": None,
                "internalId": "1",
                "externalId": None,
                "type": "subsidiary",
            },
            "location": {
                "name": None,
                "internalId": "2",
                "externalId": None,
                "type": "location",
            },
            "approvalStatus": None,
            "nextApprover": None,
            "vatRegNum": None,
            "postingPeriod": None,
            "tranDate": "2021-11-11T17:33:24",
            "currencyName": None,
            "billingAddress": None,
            "exchangeRate": None,
            "entityTaxRegNum": None,
            "taxPointDate": None,
            "terms": None,
            "dueDate": None,
            "discountDate": None,
            "tranId": None,
            "userTotal": None,
            "discountAmount": None,
            "taxTotal": None,
            "paymentHold": None,
            "memo": "Reimbursable expenses by admin1@fylefornt.com",
            "tax2Total": None,
            "creditLimit": None,
            "availableVendorCredit": None,
            "currency": {
                "name": None,
                "internalId": "1",
                "externalId": None,
                "type": "currency",
            },
            "status": None,
            "landedCostMethod": None,
            "landedCostPerLine": None,
            "transactionNumber": None,
            "expenseList": [
                {
                    "orderDoc": None,
                    "orderLine": None,
                    "line": None,
                    "category": None,
                    "account": {
                        "name": None,
                        "internalId": "65",
                        "externalId": None,
                        "type": "account",
                    },
                    "amount": 99.0,
                    "memo": "admin1@fylefornt.com - Food - 2021-11-08 - C/2021/11/R/2",
                    "grossAmt": 99.0,
                    "taxDetailsReference": None,
                    "department": {
                        "name": None,
                        "internalId": None,
                        "externalId": None,
                        "type": "department",
                    },
                    "class": {
                        "name": None,
                        "internalId": None,
                        "externalId": None,
                        "type": "classification",
                    },
                    "location": {
                        "name": None,
                        "internalId": "2",
                        "externalId": None,
                        "type": "location",
                    },
                    "customer": {
                        "name": None,
                        "internalId": None,
                        "externalId": None,
                        "type": "customer",
                    },
                    "customFieldList": [
                        {
                            "scriptId": "custcolfyle_expense_url",
                            "type": "String",
                            "value": "https://staging.fyle.tech/app/main/#/enterprise/view_expense/txiRmGpGNHyT?org_id=orf6t6jWUnpx",
                        }
                    ],
                    "isBillable": None,
                    "projectTask": None,
                    "tax1Amt": None,
                    "taxAmount": None,
                    "taxCode": {
                        "name": None,
                        "internalId": None,
                        "externalId": None,
                        "type": "classification",
                    },
                    "taxRate1": None,
                    "taxRate2": None,
                    "amortizationSched": None,
                    "amortizStartDate": None,
                    "amortizationEndDate": None,
                    "amortizationResidual": None,
                }
            ],
            "accountingBookDetailList": None,
            "itemList": None,
            "landedCostsList": None,
            "purchaseOrderList": None,
            "taxDetailsList": None,
            "customFieldList": None,
            "internalId": None,
            "externalId": "bill 1258 - admin1@fylefornt.com",
        }
    ],
    "bill_response": [
        ["name", None],
        ["internalId", "115043"],
        ["externalId", "bill 1405 - admin1@fylefornt.com"],
        ["type", "vendorBill"],
    ],
    "expense_report_payload": [
        {
            'nullFieldList': None,
            'createdDate': None,
            'lastModifiedDate': None,
            'status': None,
            'customForm': None,
            'account': {
                'name': None,
                'internalId': '118',
                'externalId': None,
                'type': 'account',
            },
            'entity': {
                'name': None,
                'internalId': '1676',
                'externalId': None,
                'type': 'vendor',
            },
            'expenseReportCurrency': {
                'name': None,
                'internalId': '1',
                'externalId': None,
                'type': 'currency',
            },
            'subsidiary': {
                'name': None,
                'internalId': '3',
                'externalId': None,
                'type': 'subsidiary',
            },
            'expenseReportExchangeRate': None,
            'taxPointDate': None,
            'tranId': None,
            'acctCorpCardExp': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'account',
            },
            'postingPeriod': None,
            'tranDate': '2021-12-08T08:30:18',
            'dueDate': None,
            'approvalStatus': None,
            'total': None,
            'nextApprover': None,
            'advance': None,
            'tax1Amt': None,
            'amount': None,
            'memo': 'Reimbursable expenses by ashwin.t@fyle.in',
            'complete': None,
            'supervisorApproval': True,
            'accountingApproval': True,
            'useMultiCurrency': None,
            'tax2Amt': None,
            'department': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'department',
            },
            'class': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'classification',
            },
            'location': {
                'name': None,
                'internalId': '8',
                'externalId': None,
                'type': 'location',
            },
            'expenseList': [{
                'amount': 50.0,
                'category': {
                    'name': None,
                    'internalId': '13',
                    'externalId': None,
                    'type': 'account',
                },
                'corporateCreditCard': None,
                'currency': {
                    'name': None,
                    'internalId': '1',
                    'externalId': None,
                    'type': 'currency',
                },
                'customer': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'customer',
                },
                'location': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'location',
                },
                'department': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'department',
                },
                'class': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'classification',
                },
                'customFieldList': [{'scriptId': 'custcolfyle_expense_url',
                                     'type': 'String',
                                     'value': 'https://staging.fyle.tech/app/main/#/enterprise/view_expense/txjvDntD9ZXR?org_id=or79Cob97KSh'
                                     }],
                'exchangeRate': None,
                'expenseDate': '2021-12-08T08:30:18',
                'expMediaItem': None,
                'foreignAmount': None,
                'grossAmt': 50.0,
                'isBillable': None,
                'isNonReimbursable': None,
                'line': None,
                'memo': 'ashwin.t@fyle.in - Accounts Payable - 2021-11-15 - C/2021/11/R/5 - ',
                'quantity': None,
                'rate': None,
                'receipt': None,
                'refNumber': None,
                'tax1Amt': None,
                'taxCode': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'taxGroup',
                },
                'taxRate1': None,
                'taxRate2': None,
            }],
            'accountingBookDetailList': None,
            'customFieldList': None,
            'internalId': None,
            'externalId': 'report 1 - ashwin.t@fyle.in',
        }
    ],
    'bill_payload': [
        {
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
                'internalId': '25',
                'externalId': None,
                'type': 'account',
            },
            'entity': {
                'name': None,
                'internalId': '1674',
                'externalId': None,
                'type': 'vendor',
            },
            'subsidiary': {
                'name': None,
                'internalId': '3',
                'externalId': None,
                'type': 'subsidiary',
            },
            'location': {
                'name': None,
                'internalId': '8',
                'externalId': None,
                'type': 'location',
            },
            'approvalStatus': None,
            'nextApprover': None,
            'vatRegNum': None,
            'postingPeriod': None,
            'tranDate': '2021-12-08T09:57:01',
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
            'memo': 'Credit card expenses by ashwin.t@fyle.in',
            'tax2Total': None,
            'creditLimit': None,
            'availableVendorCredit': None,
            'currency': {
                'name': None,
                'internalId': '1',
                'externalId': None,
                'type': 'currency',
            },
            'status': None,
            'landedCostMethod': None,
            'landedCostPerLine': None,
            'transactionNumber': None,
            'expenseList': [{
                'orderDoc': None,
                'orderLine': None,
                'line': None,
                'category': None,
                'account': {
                    'name': None,
                    'internalId': '65',
                    'externalId': None,
                    'type': 'account',
                },
                'amount': 100.0,
                'memo': 'ashwin.t@fyle.in - Accounts Payable - 2021-11-15 - C/2021/11/R/6 - ',
                'grossAmt': 100.0,
                'taxDetailsReference': None,
                'department': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'department',
                },
                'class': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'classification',
                },
                'location': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'location',
                },
                'customer': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'customer',
                },
                'customFieldList': [{'scriptId': 'custcolfyle_expense_url',
                                     'type': 'String',
                                     'value': 'https://staging.fyle.tech/app/main/#/enterprise/view_expense/txy6folbrG2j?org_id=or79Cob97KSh'
                                     }],
                'isBillable': None,
                'projectTask': None,
                'tax1Amt': None,
                'taxAmount': None,
                'taxCode': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'taxGroup',
                },
                'taxRate1': None,
                'taxRate2': None,
                'amortizationSched': None,
                'amortizStartDate': None,
                'amortizationEndDate': None,
                'amortizationResidual': None,
            }],
            'accountingBookDetailList': None,
            'itemList': None,
            'landedCostsList': None,
            'purchaseOrderList': None,
            'taxDetailsList': None,
            'customFieldList': None,
            'internalId': None,
            'externalId': 'bill 2 - ashwin.t@fyle.in',
        }
    ],
    'journal_entry_without_single_line': [
        {
            'accountingBook': None,
            'accountingBookDetailList': None,
            'approved': None,
            'createdDate': None,
            'createdFrom': None,
            'currency': {
                'name': None,
                'internalId': '1',
                'externalId': None,
                'type': 'currency',
            },
            'customFieldList': None,
            'customForm': None,
            'class': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'classification',
            },
            'department': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'department',
            },
            'location': {
                'name': None,
                'internalId': '10',
                'externalId': None,
                'type': 'location',
            },
            'exchangeRate': None,
            'isBookSpecific': None,
            'lastModifiedDate': None,
            'lineList': [{
                'account': {
                    'name': None,
                    'internalId': '228',
                    'externalId': None,
                    'type': 'account',
                },
                'department': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'department',
                },
                'location': {
                    'name': None,
                    'internalId': '10',
                    'externalId': None,
                    'type': 'location',
                },
                'class': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'classification',
                },
                'entity': {
                    'name': None,
                    'internalId': '10491',
                    'externalId': None,
                    'type': 'vendor',
                },
                'credit': 120.0,
                'creditTax': None,
                'customFieldList': [{'scriptId': 'custcolfyle_expense_url',
                                     'type': 'String',
                                     'value': 'https://staging.fyle.tech/app/main/#/enterprise/view_expense/tx7A5QpesrV5?org_id=orHe8CpW2hyN'
                                     }],
                'debit': None,
                'debitTax': None,
                'eliminate': None,
                'endDate': None,
                'grossAmt': None,
                'line': None,
                'lineTaxCode': None,
                'lineTaxRate': None,
                'memo': 'admin1@fyleforintacct.in - Food - 2021-12-03 - C/2021/12/R/1 - ',
                'residual': None,
                'revenueRecognitionRule': None,
                'schedule': None,
                'scheduleNum': None,
                'startDate': None,
                'tax1Acct': None,
                'taxAccount': None,
                'taxBasis': None,
                'tax1Amt': None,
                'taxCode': None,
                'taxRate1': None,
                'totalAmount': None,
            }, {
                'account': {
                    'name': None,
                    'internalId': '65',
                    'externalId': None,
                    'type': 'account',
                },
                'department': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'department',
                },
                'location': {
                    'name': None,
                    'internalId': '10',
                    'externalId': None,
                    'type': 'location',
                },
                'class': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'classification',
                },
                'entity': {
                    'name': None,
                    'internalId': '10491',
                    'externalId': None,
                    'type': 'vendor',
                },
                'credit': None,
                'creditTax': None,
                'customFieldList': [{'scriptId': 'custcolfyle_expense_url',
                                     'type': 'String',
                                     'value': 'https://staging.fyle.tech/app/main/#/enterprise/view_expense/tx7A5QpesrV5?org_id=orHe8CpW2hyN'
                                     }],
                'debit': 120.0,
                'debitTax': None,
                'eliminate': None,
                'endDate': None,
                'grossAmt': None,
                'line': None,
                'lineTaxCode': None,
                'lineTaxRate': None,
                'memo': 'admin1@fyleforintacct.in - Food - 2021-12-03 - C/2021/12/R/1 - ',
                'residual': None,
                'revenueRecognitionRule': None,
                'schedule': None,
                'scheduleNum': None,
                'startDate': None,
                'tax1Acct': None,
                'taxAccount': None,
                'taxBasis': None,
                'tax1Amt': None,
                'taxCode': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'taxGroup',
                },
                'taxRate1': None,
                'totalAmount': None,
            }],
            'memo': 'Reimbursable expenses by admin1@fyleforintacct.in',
            'nexus': None,
            'parentExpenseAlloc': None,
            'postingPeriod': None,
            'reversalDate': None,
            'reversalDefer': None,
            'reversalEntry': None,
            'subsidiary': {
                'name': None,
                'internalId': '5',
                'externalId': None,
                'type': 'subsidiary',
            },
            'subsidiaryTaxRegNum': None,
            'taxPointDate': None,
            'toSubsidiary': None,
            'tranDate': '2021-12-08T10:33:44',
            'tranId': None,
            'externalId': 'journal 47 - admin1@fyleforintacct.in',
        }
    ],
    'credit_card_charge': [
        {
            'account': {'internalId': '228'},
            'entity': {'internalId': '12104'},
            'subsidiary': {'internalId': '5'},
            'location': {'internalId': '10'},
            'currency': {'internalId': '1'},
            'tranDate': '12/03/2021',
            'memo': 'Credit card expenses by admin1@fyleforintacct.in',
            'expenses': [{
                'account': {'internalId': '65'},
                'amount': 130.0,
                'memo': 'admin1@fyleforintacct.in - Food - 2021-12-03 - C/2021/12/R/1 - ',
                'grossAmt': 130.0,
                'department': {'internalId': None},
                'class': {'internalId': None},
                'location': {'internalId': None},
                'customer': {'internalId': None},
                'customFieldList': [{'scriptId': 'custcolfyle_expense_url',
                                     'value': 'https://staging.fyle.tech/app/main/#/enterprise/view_expense/txcKVVELn1Vl?org_id=orHe8CpW2hyN'
                                     }],
                'isBillable': False,
                'taxAmount': None,
                'taxCode': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'taxGroup',
                },
            }],
            'externalId': 'cc-charge 48 - admin1@fyleforintacct.in',
        }
    ],
    'credit_card_charge': [
        {
            'account': {'internalId': '228'},
            'entity': {'internalId': '12104'},
            'subsidiary': {'internalId': '5'},
            'location': {'internalId': '10'},
            'currency': {'internalId': '1'},
            'tranDate': '12/03/2021',
            'memo': 'Credit card expenses by admin1@fyleforintacct.in',
            'expenses': [{
                'account': {'internalId': '65'},
                'amount': 130.0,
                'memo': 'admin1@fyleforintacct.in - Food - 2021-12-03 - C/2021/12/R/1 - ',
                'grossAmt': 130.0,
                'department': {'internalId': None},
                'class': {'internalId': None},
                'location': {'internalId': None},
                'customer': {'internalId': None},
                'customFieldList': [{'scriptId': 'custcolfyle_expense_url',
                                     'value': 'https://staging.fyle.tech/app/main/#/enterprise/view_expense/txcKVVELn1Vl?org_id=orHe8CpW2hyN'
                                     }],
                'isBillable': False,
                'taxAmount': None,
                'taxCode': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'taxGroup',
                },
            }],
            'externalId': 'cc-charge 48 - admin1@fyleforintacct.in',
        }
    ],
    'get_bill_response': [
        {
            'nullFieldList': None,
            'createdDate': "datetime.datetime(2017, 10, 3, 14, 34, 19, tzinfo=<FixedOffset '-07:00'>)",
            'lastModifiedDate': "datetime.datetime(2019, 6, 14, 6, 35, 47, tzinfo=<FixedOffset '-07:00'>)",
            'nexus': None,
            'subsidiaryTaxRegNum': None,
            'taxRegOverride': None,
            'taxDetailsOverride': None,
            'customForm': {
                'name': 'Z - Vendor Bill',
                'internalId': '153',
                'externalId': None,
                'type': None
            },
            'billAddressList': None,
            'account': {
                'name': '2000 Accounts Payable',
                'internalId': '25',
                'externalId': None,
                'type': None
            },
            'entity': {
                'name': 'UPS',
                'internalId': '32',
                'externalId': None,
                'type': None
            },
            'subsidiary': {
                'name': 'Honeycomb Mfg.',
                'internalId': '1',
                'externalId': None,
                'type': None
            },
            'approvalStatus': {
                'name': 'Approved',
                'internalId': '2',
                'externalId': None,
                'type': None
            },
            'nextApprover': None,
            'vatRegNum': None,
            'postingPeriod': None,
            'tranDate': "datetime.datetime(2017, 8, 1, 0, 0, tzinfo=<FixedOffset '-07:00'>)",
            'currencyName': 'USA',
            'billingAddress': None,
            'exchangeRate': 1.0,
            'entityTaxRegNum': None,
            'taxPointDate': None,
            'terms': {
                'name': 'Net 15',
                'internalId': '1',
                'externalId': None,
                'type': None
            },
            'dueDate': "datetime.datetime(2019, 4, 11, 0, 0, tzinfo=<FixedOffset '-07:00'>)",
            'discountDate': None,
            'tranId': None,
            'userTotal': 344.25,
            'discountAmount': None,
            'taxTotal': None,
            'paymentHold': False,
            'memo': '913465',
            'tax2Total': None,
            'creditLimit': None,
            'availableVendorCredit': None,
            'currency': {
                'name': 'USA',
                'internalId': '1',
                'externalId': None,
                'type': None
            },
            'class': None,
            'department': None,
            'location': None,
            'status': 'Open',
            'landedCostMethod': '_weight',
            'landedCostPerLine': False,
            'transactionNumber': None,
            'expenseList': {
                'expense': [
                    {
                        'orderDoc': None,
                        'orderLine': None,
                        'line': 1,
                        'category': None,
                        'account': {
                            'name': '6170 Postage & Delivery',
                            'internalId': '86',
                            'externalId': None,
                            'type': None
                        },
                        'amount': 344.25,
                        'taxAmount': None,
                        'tax1Amt': None,
                        'memo': None,
                        'grossAmt': None,
                        'taxDetailsReference': None,
                        'department': None,
                        'class': None,
                        'location': None,
                        'customer': None,
                        'isBillable': False,
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
                ],
                'replaceAll': 'true'
            },
            'accountingBookDetailList': None,
            'itemList': None,
            'landedCostsList': {
                'landedCost': [
                    {
                        'category': {
                            'name': 'Landed Cost - Duty',
                            'internalId': '1',
                            'externalId': None,
                            'type': None
                        },
                        'amount': None,
                        'source': None,
                        'transaction': None
                    },
                    {
                        'category': {
                            'name': 'Landed Cost - Freight',
                            'internalId': '2',
                            'externalId': None,
                            'type': None
                        },
                        'amount': None,
                        'source': None,
                        'transaction': None
                    }
                ],
                'replaceAll': 'true'
            },
            'purchaseOrderList': None,
            'taxDetailsList': None,
            'customFieldList': {
                'customField': [
                    {
                        'value': False,
                        'internalId': '223',
                        'scriptId': 'custbody_powf_se_ok'
                    },
                    {
                        'value': False,
                        'internalId': '220',
                        'scriptId': 'custbody_powf_ctrl_ok'
                    }
                ]
            },
            'internalId': '238',
            'externalId': 'tran1311'
        }
    ],
    'get_expense_report_response': [
        {
            'nullFieldList': None,
            'createdDate': "datetime.datetime(2021, 7, 29, 5, 19, 52, tzinfo= < FixedOffset '-07:00' > )",
            'lastModifiedDate': "datetime.datetime(2021, 7, 29, 5, 19, 52, tzinfo= < FixedOffset '-07:00' > )",
            'status': 'Approved by Accounting',
            'customForm': {
                'name': 'Custom flocatio Report',
                'internalId': '250',
                'externalId': None,
                'type': None
            },
            'account': {
                'name': '2000 Accounts Payable',
                'internalId': '25',
                'externalId': None,
                'type': None
            },
            'entity': {
                'name': 'Ashwin',
                'internalId': '3780',
                'externalId': None,
                'type': None
            },
            'expenseReportCurrency': {
                'name': 'USA',
                'internalId': '1',
                'externalId': None,
                'type': None
            },
            'expenseReportExchangeRate': 1.0,
            'subsidiary': {
                'name': 'Honeycomb Mfg.',
                'internalId': '1',
                'externalId': None,
                'type': None
            },
            'taxPointDate': None,
            'tranId': 'EXP00002819',
            'acctCorpCardExp': None,
            'postingPeriod': None,
            'tranDate': "datetime.datetime(2002, 1, 9, 0, 0, tzinfo= < FixedOffset '-08:00' > )",
            'dueDate': "datetime.datetime(2002, 1, 9, 0, 0, tzinfo= < FixedOffset '-08:00' > )",
            'approvalStatus': None,
            'total': 667.0,
            'nextApprover': None,
            'advance': None,
            'tax1Amt': None,
            'amount': 667.0,
            'memo': 'Reimbursable expenses by ashwin.t@fyle.in',
            'complete': True,
            'supervisorApproval': None,
            'accountingApproval': True,
            'useMultiCurrency': True,
            'tax2Amt': None,
            'department': None,
            'class': None,
            'location': None,
            'expenseList': {
                'expense': [
                    {
                        'line': 1,
                        'expenseDate': "datetime.datetime(2002, 1, 9, 0, 0, tzinfo= < FixedOffset '-08:00' > )",
                        'category': {
                            'name': 'Airfare',
                            'internalId': '6',
                            'externalId': None,
                            'type': None
                        },
                        'quantity': None,
                        'rate': None,
                        'foreignAmount': 667.0,
                        'currency': {
                            'name': 'USA',
                            'internalId': '1',
                            'externalId': None,
                            'type': None
                        },
                        'exchangeRate': 1.0,
                        'amount': 667.0,
                        'taxCode': None,
                        'memo': 'ashwin.t@fyle.in - Accounts Payable - 2002-01-09 - C/2021/07/R/6 - ',
                        'taxRate1': None,
                        'tax1Amt': None,
                        'department': None,
                        'grossAmt': None,
                        'taxRate2': None,
                        'class': None,
                        'customer': None,
                        'location': {
                            'name': '01: San Francisco',
                            'internalId': '2',
                            'externalId': None,
                            'type': None
                        },
                        'isBillable': False,
                        'expMediaItem': None,
                        'isNonReimbursable': False,
                        'corporateCreditCard': False,
                        'receipt': None,
                        'refNumber': 1,
                        'customFieldList': {
                            'customField': [
                                {
                                    'value': 'https://staging.fyle.tech/app/main/#/enterprise/view_expense/tx7b3e705y5p?org_id=or7m5SVD9Rv1',
                                    'internalId': '4584',
                                    'scriptId': 'custcolfyle_expense_url'
                                }
                            ]
                        }
                    }
                ],
                'replaceAll': 'true'
            },
            'accountingBookDetailList': None,
            'customFieldList': None,
            'internalId': '85327',
            'externalId': 'report 1255 - ashwin.t@fyle.in'
        }
    ]
}
