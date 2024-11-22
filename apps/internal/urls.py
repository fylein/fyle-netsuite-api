import itertools

from django.urls import path

from .views import AccountingFieldsView, ExportedEntryView

urlpatterns = [
    path('accounting_fields/', AccountingFieldsView.as_view(), name='accounting-fields'),
    path('exported_entry/', ExportedEntryView.as_view(), name='exported-entry'),
]
