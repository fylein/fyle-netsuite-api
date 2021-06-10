from django.urls import path, include

from .views import WorkspaceView, ReadyView, ConnectFyleView, ConnectNetSuiteView, ScheduleView, ConfigurationsView

urlpatterns = [
    path('', WorkspaceView.as_view({'get': 'get', 'post': 'post'})),
    path('<int:workspace_id>/schedule/', ScheduleView.as_view({'post': 'post', 'get': 'get'})),
    path('<int:workspace_id>/configuration/', ConfigurationsView.as_view()),
    path('<int:workspace_id>/credentials/fyle/', ConnectFyleView.as_view({'get': 'get'})),
    path('ready/', ReadyView.as_view({'get': 'get'})),
    path('<int:workspace_id>/connect_netsuite/tba/', ConnectNetSuiteView.as_view({'post': 'post'})),
    path('<int:workspace_id>/credentials/netsuite/', ConnectNetSuiteView.as_view({'get': 'get'})),
    path('<int:workspace_id>/fyle/', include('apps.fyle.urls')),
    path('<int:workspace_id>/netsuite/', include('apps.netsuite.urls')),
    path('<int:workspace_id>/tasks/', include('apps.tasks.urls')),
    path('<int:workspace_id>/mappings/', include('apps.mappings.urls')),
    path('<int:workspace_id>/mappings/', include('fyle_accounting_mappings.urls'))
]

