from django.urls import path

from .views import EmployeeMappingView, CategoryMappingView, \
    CostCenterMappingView, ProjectMappingView

urlpatterns = [
    path('employees/', EmployeeMappingView.as_view()),
    path('categories/', CategoryMappingView.as_view()),
    path('cost_centers/', CostCenterMappingView.as_view()),
    path('projects/', ProjectMappingView.as_view())
]
