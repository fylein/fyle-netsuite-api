from django.urls import path

from apps.workspaces.apis.map_employees.views import MapEmployeesView
from apps.workspaces.apis.export_settings.views import ExportSettingsView


urlpatterns = [
    path('<int:workspace_id>/map_employees/', MapEmployeesView.as_view()),
    path('<int:workspace_id>/export_settings/', ExportSettingsView.as_view()),
]
