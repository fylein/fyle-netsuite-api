from django.urls import path, include

from .views import WorkspaceView, ReadyView, ConnectFyleView, ConnectNetSuiteView, ScheduleView, GeneralSettingsView,\
    ScheduledSyncView

urlpatterns = [
    path('', WorkspaceView.as_view({'get': 'get', 'post': 'post'}), name='workspace'),
    path('<int:workspace_id>/', WorkspaceView.as_view({'get': 'get_by_id'}), name='workspace-by-id'),
    path('<int:workspace_id>/schedule/', ScheduleView.as_view({'post': 'post', 'get': 'get'}),
         name='workspace-schedule'),
    path('<int:workspace_id>/settings/general/', GeneralSettingsView.as_view({'post': 'post', 'get': 'get'}),
         name='workspace-general-settings'),
    path('<int:workspace_id>/schedule/trigger/', ScheduledSyncView.as_view({'post': 'post'}),
         name='workspace-schedule-trigger'),
    path('<int:workspace_id>/connect_fyle/authorization_code/', ConnectFyleView.as_view({'post': 'post'}),
         name='connect-fyle'),
    path('<int:workspace_id>/credentials/fyle/', ConnectFyleView.as_view({'get': 'get'}), name='fyle-credentials'),
    path('<int:workspace_id>/credentials/fyle/delete/', ConnectFyleView.as_view({'post': 'delete'}),
         name='delete-fyle-credentials'),
    path('ready/', ReadyView.as_view({'get': 'get'}), name='ready'),
    path('<int:workspace_id>/connect_netsuite/tba/', ConnectNetSuiteView.as_view({'post': 'post'}),
         name='netsuite-connection'),
    path('<int:workspace_id>/credentials/netsuite/', ConnectNetSuiteView.as_view({'get': 'get'}),
         name='netsuite-credentials'),
    path('<int:workspace_id>/credentials/netsuite/delete/', ConnectNetSuiteView.as_view({'post': 'delete'}),
         name='delete-netsuite-credentials'),
    path('<int:workspace_id>/fyle/', include('apps.fyle.urls')),
    path('<int:workspace_id>/netsuite/', include('apps.netsuite.urls')),
    path('<int:workspace_id>/tasks/', include('apps.tasks.urls')),
    path('<int:workspace_id>/mappings/', include('apps.mappings.urls')),
    path('<int:workspace_id>/mappings/', include('fyle_accounting_mappings.urls'))
]

