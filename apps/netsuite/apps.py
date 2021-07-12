from django.apps import AppConfig


class NetsuiteConfig(AppConfig):
    name = 'apps.netsuite'

    def ready(self):
        super(NetsuiteConfig, self).ready()
        import apps.netsuite.signals
