from django.urls import path

from .views import GeneralMappingView, SubsidiaryMappingView, AutoMapEmployeeView

urlpatterns = [
    path('subsidiaries/', SubsidiaryMappingView.as_view(), name='subsidiaries'),
    path('general/', GeneralMappingView.as_view(), name='general-mappings'),
    path('auto_map_employees/trigger/', AutoMapEmployeeView.as_view(), name='auto-map-employees-trigger')
]
