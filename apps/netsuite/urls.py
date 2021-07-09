from django.urls import path

from .views import SubsidiaryView, BillScheduleView, ExpenseReportScheduleView, JournalEntryScheduleView,\
    NetSuiteFieldsView, SyncCustomFieldsView, CustomSegmentView, ReimburseNetSuitePaymentsView, \
    VendorPaymentView, SyncNetSuiteDimensionView, RefreshNetSuiteDimensionView, CreditCardChargeScheduleView,\
    NetSuiteAttributesCountView

urlpatterns = [
    path('subsidiaries/', SubsidiaryView.as_view(), name='subsidiaries'),
    path('bills/trigger/', BillScheduleView.as_view(), name='trigger-bills'),
    path('expense_reports/trigger/', ExpenseReportScheduleView.as_view(), name='trigger-expense-reports'),
    path('journal_entries/trigger/', JournalEntryScheduleView.as_view(), name='trigger-journal-entries'),
    path('credit_card_charges/trigger/', CreditCardChargeScheduleView.as_view(), name='trigger-credit-card-charges'),
    path('netsuite_fields/', NetSuiteFieldsView.as_view(), name='netsuite-fields'),
    path('attributes/count/', NetSuiteAttributesCountView.as_view(), name='attributes-count'),
    path('custom_fields/', SyncCustomFieldsView.as_view(), name='custom-fields'),
    path('custom_segments/', CustomSegmentView.as_view(), name='custom-segments'),
    path('vendor_payments/', VendorPaymentView.as_view(), name='vendor-payments'),
    path('reimburse_payments/', ReimburseNetSuitePaymentsView.as_view(), name='reimburse-payments'),
    path('sync_dimensions/', SyncNetSuiteDimensionView.as_view(), name='sync-dimensions'),
    path('refresh_dimensions/', RefreshNetSuiteDimensionView.as_view(), name='refresh-dimensions')
]
