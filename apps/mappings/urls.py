from django.urls import path

from .views import GeneralMappingView, SubsidiaryMappingView, AutoMapEmployeeView, MappingSettingsView

urlpatterns = [
    path('subsidiaries/', SubsidiaryMappingView.as_view()),
    path('general/', GeneralMappingView.as_view()),
    path('auto_map_employees/trigger/', AutoMapEmployeeView.as_view()),
    path('settings/', MappingSettingsView.as_view())
]
