import itertools

from django.urls import path

from .views import NetSuiteFieldsView, DestinationAttributesView, CustomSegmentView, \
    SyncNetSuiteDimensionView, RefreshNetSuiteDimensionView, TriggerExportsView, TriggerPaymentsView, \
    DestinationAttributesCountView

netsuite_app_paths = [
    path('netsuite_fields/', NetSuiteFieldsView.as_view(), name='netsuite-fields'),
    path('destination_attributes/', DestinationAttributesView.as_view(), name='destination-attributes'),
    path('destination_attributes/count/', DestinationAttributesCountView.as_view(), name='attributes-count'),
    path('custom_segments/', CustomSegmentView.as_view(), name='custom-segments'),
    path('exports/trigger/', TriggerExportsView.as_view(), name='trigger-exports'),
    path('payments/trigger/', TriggerPaymentsView.as_view(), name='trigger-payments'),
]

netsuite_dimension_paths = [
    path('sync_dimensions/', SyncNetSuiteDimensionView.as_view(), name='sync-dimensions'),
    path('refresh_dimensions/', RefreshNetSuiteDimensionView.as_view(), name='refresh-dimensions')
]

urlpatterns = list(itertools.chain(netsuite_app_paths, netsuite_dimension_paths))
