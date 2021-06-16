from django.apps import AppConfig


class WorkspacesConfig(AppConfig):
    name = 'apps.workspaces'

    def ready(self):
        super(WorkspacesConfig, self).ready()
        import apps.workspaces.signals
