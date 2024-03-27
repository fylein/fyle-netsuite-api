from django.urls import path
from apps.workspaces.apis.advanced_settings.views import AdvancedSettingsView

from apps.workspaces.apis.map_employees.views import MapEmployeesView
from apps.workspaces.apis.export_settings.views import ExportSettingsView
from apps.workspaces.apis.import_settings.views import ImportSettingsView
from apps.workspaces.apis.errors.views import ErrorsView



urlpatterns = [
    path('<int:workspace_id>/map_employees/', MapEmployeesView.as_view(), name='map-employees'),
    path('<int:workspace_id>/export_settings/', ExportSettingsView.as_view(), name='export-settings'),
    path('<int:workspace_id>/import_settings/', ImportSettingsView.as_view(), name='import-settings'),
    path('<int:workspace_id>/advanced_configurations/', AdvancedSettingsView.as_view(), name='advanced-settings'),
    path('<int:workspace_id>/errors/', ErrorsView.as_view(), name='errors')
]
