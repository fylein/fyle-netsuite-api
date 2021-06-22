from django.urls import path, include

from .views import WorkspaceView, ReadyView, ConnectFyleView, ConnectNetSuiteView, ScheduleView, ConfigurationsView

workspaces_app_paths = [
    path('', WorkspaceView.as_view({'get': 'get', 'post': 'post'})),
    path('<int:workspace_id>/', WorkspaceView.as_view({'get': 'get_by_id'})),
    path('<int:workspace_id>/schedule/', ScheduleView.as_view({'post': 'post', 'get': 'get'})),
    path('<int:workspace_id>/configuration/', ConfigurationsView.as_view()),
    path('ready/', ReadyView.as_view({'get': 'get'}))
]

fyle_connection_api_paths = [
    path('<int:workspace_id>/connect_fyle/authorization_code/', ConnectFyleView.as_view({'post': 'post'})),
    path('<int:workspace_id>/credentials/fyle/', ConnectFyleView.as_view({'get': 'get'})),
    path('<int:workspace_id>/credentials/fyle/delete/', ConnectFyleView.as_view({'post': 'delete'}))
]

netsuite_connection_api_paths = [
    path('<int:workspace_id>/connect_netsuite/tba/', ConnectNetSuiteView.as_view({'post': 'post'})),
    path('<int:workspace_id>/credentials/netsuite/', ConnectNetSuiteView.as_view({'get': 'get'})),
    path('<int:workspace_id>/credentials/netsuite/delete/', ConnectNetSuiteView.as_view({'post': 'delete'}))
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
