import itertools

from django.urls import path

from .views import AccountingFieldsView

urlpatterns = [
    path('accounting_fields/', AccountingFieldsView.as_view(), name='accounting-fields'),
]
