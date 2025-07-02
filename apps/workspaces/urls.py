from django.urls import path, include

from .views import ExportToNetsuiteView, LastExportDetailView, WorkspaceView, WorkspaceAdminsView, ReadyView, ConnectFyleView, ConnectNetSuiteView, ConfigurationsView, SetupE2ETestView, TokenHealthView

workspaces_app_paths = [
    path('', WorkspaceView.as_view({'get': 'get', 'post': 'post'}), name='workspace'),
    path('<int:workspace_id>/', WorkspaceView.as_view({'get': 'get_by_id'}), name='workspace-by-id'),
    path('<int:workspace_id>/configuration/', ConfigurationsView.as_view(), name='workspace-configurations'),
    path('ready/', ReadyView.as_view({'get': 'get'}), name='ready'),
    path('<int:workspace_id>/admins/', WorkspaceAdminsView.as_view({'get': 'get'}), name='admin'),
    path('<int:workspace_id>/setup_e2e_test/', SetupE2ETestView.as_view({'post': 'post'}), name='setup-e2e-test'),
    path('<int:workspace_id>/export_detail/', LastExportDetailView.as_view(), name='export-detail'),
    path('<int:workspace_id>/exports/trigger/', ExportToNetsuiteView.as_view({'post': 'post'}), name='export-to-netsuite'),
]

fyle_connection_api_paths = [
    path('<int:workspace_id>/connect_fyle/authorization_code/', ConnectFyleView.as_view({'post': 'post'}),
         name='connect-fyle'),
    path('<int:workspace_id>/credentials/fyle/', ConnectFyleView.as_view({'get': 'get'}), name='get-fyle-credentials'),
    path('<int:workspace_id>/credentials/fyle/delete/', ConnectFyleView.as_view({'post': 'delete'}),
         name='delete-fyle-credentials')
]

netsuite_connection_api_paths = [
    path('<int:workspace_id>/connect_netsuite/tba/', ConnectNetSuiteView.as_view({'post': 'post'}),
         name='post-netsuite-credentials'),
    path('<int:workspace_id>/credentials/netsuite/', ConnectNetSuiteView.as_view({'get': 'get'}),
         name='get-netsuite-credentials'),
    path('<int:workspace_id>/credentials/netsuite/delete/', ConnectNetSuiteView.as_view({'post': 'delete'}),
         name='delete-netsuite-credentials'),
    path('<int:workspace_id>/token_health/', TokenHealthView.as_view({'get': 'get'})),
]

other_app_paths = [
    path('<int:workspace_id>/fyle/', include('apps.fyle.urls')),
    path('<int:workspace_id>/netsuite/', include('apps.netsuite.urls')),
    path('<int:workspace_id>/tasks/', include('apps.tasks.urls')),
    path('<int:workspace_id>/mappings/', include('apps.mappings.urls')),
    path('<int:workspace_id>/mappings/', include('fyle_accounting_mappings.urls'))
]

urlpatterns = []
urlpatterns.extend(workspaces_app_paths)
urlpatterns.extend(fyle_connection_api_paths)
urlpatterns.extend(netsuite_connection_api_paths)
urlpatterns.extend(other_app_paths)
