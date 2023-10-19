from django.urls import path

from apps.workspaces.apis.map_employees.views import MapEmployeesView


urlpatterns = [
    path('<int:workspace_id>/map_employees/', MapEmployeesView.as_view()),
]
