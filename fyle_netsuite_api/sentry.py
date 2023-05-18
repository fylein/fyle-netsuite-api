import os

import sentry_sdk

from sentry_sdk.integrations.django import DjangoIntegration
import gevent

class Sentry:

    @staticmethod
    def init():
        sentry_sdk.init(
            dsn=os.environ.get('SENTRY_DSN'),
            send_default_pii=True,
            integrations=[DjangoIntegration()],
            environment=os.environ.get('SENTRY_ENV'),
            traces_sampler=Sentry.traces_sampler,
            attach_stacktrace=True,
            before_send=Sentry.before_send,
            request_bodies='small',
            in_app_include=['apps.users',
            'apps.workspaces',
            'apps.mappings',
            'apps.fyle',
            'apps.netsuite',
            'apps.tasks',
            'fyle_rest_auth',
            'fyle_accounting_mappings'],
        )

    @staticmethod
    def traces_sampler(sampling_context):
        # avoiding ready APIs in performance tracing
        if sampling_context.get('wsgi_environ') is not None:
            if 'ready/' in sampling_context['wsgi_environ']['PATH_INFO']:
                return 0

        return 1
    @staticmethod
    def before_send(event, hint):
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info'] 
            if isinstance(exc_value, (gevent.GreenletExit)):
                return None
            elif exc_value.args[0] in ['Error: 502']:
                return None
        return event
