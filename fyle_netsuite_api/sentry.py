import os
from typing import Any, Dict, Optional

import gevent
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


class Sentry:
    SENSITIVE_FIELDS = {
        'password', 'secret', 'passwd', 'api_key', 'apikey', 'access_token',
        'auth_token', 'credentials', 'email', 'workspace_name', 'workspace_id',
        'org_name', 'user_email'
    }

    @staticmethod
    def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values."""
        sanitized = {}
        for key, value in data.items():
            # Check if the key contains sensitive information
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in Sentry.SENSITIVE_FIELDS):
                sanitized[key] = '[Filtered]'
            elif isinstance(value, dict):
                sanitized[key] = Sentry._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    Sentry._sanitize_dict(item) if isinstance(item, dict)
                    else '[Filtered]' if any(sensitive in str(item).lower() for sensitive in Sentry.SENSITIVE_FIELDS)
                    else item
                    for item in value
                ]
            elif isinstance(value, str) and any(sensitive in value.lower() for sensitive in Sentry.SENSITIVE_FIELDS):
                sanitized[key] = '[Filtered]'
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def init():
        sentry_sdk.init(
            dsn=os.environ.get('SENTRY_DSN'),
            send_default_pii=False,
            integrations=[
                DjangoIntegration(),
            ],
            environment=os.environ.get('SENTRY_ENV'),
            attach_stacktrace=True,
            before_send=Sentry.before_send,
            before_breadcrumb=Sentry.before_breadcrumb,
            max_request_body_size='small',
            in_app_include=[
                'apps.users',
                'apps.workspaces',
                'apps.mappings',
                'apps.fyle',
                'apps.netsuite',
                'apps.tasks',
                'fyle_rest_auth',
                'fyle_accounting_mappings'
            ],
            send_client_reports=False
        )

    @staticmethod
    def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter sensitive data before sending to Sentry."""
        # Handle exceptions that should not be sent
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            if isinstance(exc_value, gevent.GreenletExit):
                return None
            elif getattr(exc_value, 'args', [None])[0] in ['Error: 502']:
                return None

        # Filter sensitive data from the event
        if 'request' in event:
            if 'headers' in event['request']:
                # Filter sensitive headers
                headers = event['request']['headers']
                sensitive_headers = {'authorization', 'cookie', 'x-api-key', 'token'}
                event['request']['headers'] = {
                    k: '[Filtered]' if k.lower() in sensitive_headers else v
                    for k, v in headers.items()
                }

            # Filter request data
            if 'data' in event['request']:
                event['request']['data'] = Sentry._sanitize_dict(event['request']['data'])

        # Filter extra data
        if 'extra' in event:
            event['extra'] = Sentry._sanitize_dict(event['extra'])

        # Filter user data
        if 'user' in event:
            allowed_user_fields = {'id'}
            event['user'] = {
                k: v for k, v in event['user'].items()
                if k in allowed_user_fields
            }

        return event

    @staticmethod
    def before_breadcrumb(crumb: Dict[str, Any], hint: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Filter sensitive data from breadcrumbs."""
        # Filter out specific categories entirely
        if crumb.get('category') in {'email', 'workspace_name', 'org_name', 'user_email'}:
            return None

        # Filter sensitive data from breadcrumb data
        if 'data' in crumb:
            crumb['data'] = Sentry._sanitize_dict(crumb['data'])

        return crumb
