from django.urls import path

from .views import GeneralMappingView, SubsidiaryMappingView, AutoMapEmployeeView, PostCountryView

urlpatterns = [
    path('subsidiaries/', SubsidiaryMappingView.as_view(), name='subsidiaries'),
    path('post_country/', PostCountryView.as_view(), name='country'),
    path('general/', GeneralMappingView.as_view(), name='general-mappings'),
    path('auto_map_employees/trigger/', AutoMapEmployeeView.as_view(), name='auto-map-employees-trigger')
]
