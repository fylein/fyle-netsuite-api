from django.apps import AppConfig


class MappingsConfig(AppConfig):
    name = 'apps.mappings'

    def ready(self):
        super(MappingsConfig, self).ready()
        import apps.mappings.signals
