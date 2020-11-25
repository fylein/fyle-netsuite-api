from django.urls import path

from .views import VendorView, AccountView, DepartmentView, SubsidiaryView, BillView, BillScheduleView, \
    ClassificationView, LocationView, EmployeeView, ExpenseReportView, ExpenseReportScheduleView, JournalEntryView,\
    JournalEntryScheduleView, BankAccountView, CreditCardAccountView, AccountsPayableView, ExpenseCategoryView, \
    CurrencyView, NetSuiteFieldsView, SyncCustomFieldsView, CustomSegmentView, VendorPaymentAccountView

urlpatterns = [
    path('vendors/', VendorView.as_view()),
    path('employees/', EmployeeView.as_view()),
    path('accounts/', AccountView.as_view()),
    path('accounts_payables/', AccountsPayableView.as_view()),
    path('vendor_payment_accounts/', VendorPaymentAccountView.as_view()),
    path('bank_accounts/', BankAccountView.as_view()),
    path('credit_card_accounts/', CreditCardAccountView.as_view()),
    path('departments/', DepartmentView.as_view()),
    path('expense_categories/', ExpenseCategoryView.as_view()),
    path('locations/', LocationView.as_view()),
    path('currencies/', CurrencyView.as_view()),
    path('classifications/', ClassificationView.as_view()),
    path('subsidiaries/', SubsidiaryView.as_view()),
    path('bills/', BillView.as_view()),
    path('bills/trigger/', BillScheduleView.as_view()),
    path('expense_reports/', ExpenseReportView.as_view()),
    path('expense_reports/trigger/', ExpenseReportScheduleView.as_view()),
    path('journal_entries/', JournalEntryView.as_view()),
    path('journal_entries/trigger/', JournalEntryScheduleView.as_view()),
    path('netsuite_fields/', NetSuiteFieldsView.as_view()),
    path('custom_fields/', SyncCustomFieldsView.as_view()),
    path('custom_segments/', CustomSegmentView.as_view()),
]
