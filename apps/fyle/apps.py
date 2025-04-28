from django.apps import AppConfig


class FyleConfig(AppConfig):
    name = 'apps.fyle'

    def ready(self):
        super(FyleConfig, self).ready()
        import apps.fyle.signals
