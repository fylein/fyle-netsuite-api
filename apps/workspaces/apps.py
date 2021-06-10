from django.apps import AppConfig


class WorkspacesConfig(AppConfig):
    name = 'workspaces'

    def ready(self):
        import apps.workspaces.signals
