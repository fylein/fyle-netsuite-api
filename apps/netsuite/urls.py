from django.urls import path

from .views import SubsidiaryView, BillScheduleView, ExpenseReportScheduleView, JournalEntryScheduleView,\
    NetSuiteFieldsView, SyncCustomFieldsView, CustomSegmentView, ReimburseNetSuitePaymentsView, \
    VendorPaymentView, SyncNetSuiteDimensionView, RefreshNetSuiteDimensionView, CreditCardChargeScheduleView

urlpatterns = [
    path('subsidiaries/', SubsidiaryView.as_view()),
    path('bills/trigger/', BillScheduleView.as_view()),
    path('expense_reports/trigger/', ExpenseReportScheduleView.as_view()),
    path('journal_entries/trigger/', JournalEntryScheduleView.as_view()),
    path('credit_card_charges/trigger/', CreditCardChargeScheduleView.as_view()),
    path('netsuite_fields/', NetSuiteFieldsView.as_view()),
    path('custom_fields/', SyncCustomFieldsView.as_view()),
    path('custom_segments/', CustomSegmentView.as_view()),
    path('vendor_payments/', VendorPaymentView.as_view()),
    path('reimburse_payments/', ReimburseNetSuitePaymentsView.as_view()),
    path('sync_dimensions/', SyncNetSuiteDimensionView.as_view()),
    path('refresh_dimensions/', RefreshNetSuiteDimensionView.as_view())
]
