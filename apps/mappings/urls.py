from django.urls import path

from .views import GeneralMappingView, SubsidiaryMappingView

urlpatterns = [
    path('subsidiaries/', SubsidiaryMappingView.as_view()),
    path('general/', GeneralMappingView.as_view())
]
