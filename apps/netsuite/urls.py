from django.urls import path

from .views import VendorView, AccountView, DepartmentView, SubsidiaryView, BillView, BillScheduleView, \
    ClassificationView, LocationView, EmployeeView, ExpenseReportView, ExpenseReportScheduleView, JournalEntryView,\
    JournalEntryScheduleView, BankAccountView, CreditCardAccountView, AccountsPayableView, ExpenseCategoryView, \
    CurrencyView, NetSuiteFieldsView, SyncCustomFieldsView, CustomSegmentView, VendorPaymentAccountView,\
    ReimburseNetSuitePaymentsView, VendorPaymentView, CustomerView, ProjectView, CCCExpenseCategoryView, CCCAccountView

urlpatterns = [
    path('vendors/', VendorView.as_view(), name='vendors'),
    path('employees/', EmployeeView.as_view(), name='employees'),
    path('accounts/', AccountView.as_view(), name='accounts'),
    path('ccc_accounts/', CCCAccountView.as_view(), name='ccc-accounts'),
    path('accounts_payables/', AccountsPayableView.as_view(), name='accounts-payables'),
    path('vendor_payment_accounts/', VendorPaymentAccountView.as_view(), name='vendor-payment-accounts'),
    path('bank_accounts/', BankAccountView.as_view(), name='bank-accounts'),
    path('credit_card_accounts/', CreditCardAccountView.as_view(), name='credit-card-accounts'),
    path('departments/', DepartmentView.as_view(), name='departments'),
    path('expense_categories/', ExpenseCategoryView.as_view(), name='expense-categories'),
    path('ccc_expense_categories/', CCCExpenseCategoryView.as_view(), name='ccc-expense-categories'),
    path('locations/', LocationView.as_view(), name='locations'),
    path('currencies/', CurrencyView.as_view(), name='currencies'),
    path('classifications/', ClassificationView.as_view(), name='classifications'),
    path('customers/', CustomerView.as_view(), name='customers'),
    path('projects/', ProjectView.as_view(), name='projects'),
    path('subsidiaries/', SubsidiaryView.as_view(), name='subsidiaries'),
    path('bills/', BillView.as_view(), name='bills'),
    path('bills/trigger/', BillScheduleView.as_view(), name='bills-trigger'),
    path('expense_reports/', ExpenseReportView.as_view(), name='expense-reports'),
    path('expense_reports/trigger/', ExpenseReportScheduleView.as_view(), name='expense-reports-trigger'),
    path('journal_entries/', JournalEntryView.as_view(), name='journal-entries'),
    path('journal_entries/trigger/', JournalEntryScheduleView.as_view(), name='journal-entries-trigger'),
    path('netsuite_fields/', NetSuiteFieldsView.as_view(), name='netsuite-fields'),
    path('custom_fields/', SyncCustomFieldsView.as_view(), name='custom-fields'),
    path('custom_segments/', CustomSegmentView.as_view(), name='custom-segments'),
    path('vendor_payments/', VendorPaymentView.as_view(), name='vendor-payments'),
    path('reimburse_payments/', ReimburseNetSuitePaymentsView.as_view(), name='reimburse-payments')
]
