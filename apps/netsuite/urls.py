from django.urls import path

from .views import VendorView, AccountView, DepartmentView, SubsidiaryView, BillView, BillScheduleView, \
    ClassificationView, LocationView, EmployeeView, ExpenseReportView, ExpenseReportScheduleView, JournalEntryView,\
    JournalEntryScheduleView

urlpatterns = [
    path('vendors/', VendorView.as_view()),
    path('employees/', EmployeeView.as_view()),
    path('accounts/', AccountView.as_view({'post': 'post_accounts', 'get': 'get_accounts'})),
    path('accounts_payables/', AccountView.as_view({'get': 'accounts_payable_accounts'})),
    path('bank_accounts/', AccountView.as_view({'get': 'bank_accounts'})),
    path('credit_card_accounts/', AccountView.as_view({'get': 'credit_card_accounts'})),
    path('departments/', DepartmentView.as_view()),
    path('locations/', LocationView.as_view()),
    path('classifications/', ClassificationView.as_view()),
    path('subsidiaries/', SubsidiaryView.as_view()),
    path('bills/', BillView.as_view()),
    path('bills/trigger/', BillScheduleView.as_view()),
    path('expense_reports/', ExpenseReportView.as_view()),
    path('expense_reports/trigger/', ExpenseReportScheduleView.as_view()),
    path('journal_entries/', JournalEntryView.as_view()),
    path('journal_entries/trigger/', JournalEntryScheduleView.as_view())
]
