import itertools

from django.urls import path

from .views import NetSuiteFieldsView, DestinationAttributesView, CustomSegmentView, ReimburseNetSuitePaymentsView, \
    VendorPaymentView, SyncNetSuiteDimensionView, RefreshNetSuiteDimensionView, TriggerExportsView

netsuite_app_paths = [
    path('netsuite_fields/', NetSuiteFieldsView.as_view()),
    path('destination_attributes/', DestinationAttributesView.as_view()),
    path('custom_segments/', CustomSegmentView.as_view()),
    path('exports/trigger/', TriggerExportsView.as_view())
]

netsuite_dimension_paths = [
    path('sync_dimensions/', SyncNetSuiteDimensionView.as_view()),
    path('refresh_dimensions/', RefreshNetSuiteDimensionView.as_view())
]

trigger_payments_paths = [
    path('vendor_payments/', VendorPaymentView.as_view()),
    path('reimburse_payments/', ReimburseNetSuitePaymentsView.as_view())
]

urlpatterns = list(
    itertools.chain(netsuite_app_paths, netsuite_dimension_paths, trigger_payments_paths)
)
