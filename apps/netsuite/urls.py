from django.urls import path

from .views import VendorView, AccountView, LocationView, DepartmentView, SubsidiaryView, BillView, BillScheduleView

urlpatterns = [
    path('vendors/', VendorView.as_view()),
    path('accounts/', AccountView.as_view()),
    path('departments/', DepartmentView.as_view()),
    path('locations/', LocationView.as_view()),
    path('subsidiaries/', SubsidiaryView.as_view()),
    path('bills/', BillView.as_view()),
    path('bills/trigger/', BillScheduleView.as_view()),
]
