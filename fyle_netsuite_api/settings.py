"""
Django settings for fyle_netsuite_api project.

Generated by 'django-admin startproject' using Django 3.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""
import sys
import os

import dj_database_url

from logging.config import dictConfig
from .logging_middleware import WorkerIDFilter

from .sentry import Sentry

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if os.environ.get('DEBUG') == 'True' else False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Installed Apps
    'rest_framework',
    'corsheaders',
    'fyle_rest_auth',
    'fyle_accounting_mappings',
    'fyle_integrations_imports',

    # User Created Apps
    'apps.users',
    'apps.workspaces',
    'apps.fyle',
    'apps.tasks',
    'apps.mappings',
    'apps.netsuite',
    'django_q',
    'django_filters',
    'apps.internal'
]

MIDDLEWARE = [
    'request_logging.middleware.LoggingMiddleware',
    'fyle_netsuite_api.logging_middleware.LogPostRequestMiddleware',
    'fyle_netsuite_api.logging_middleware.ErrorHandlerMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fyle_netsuite_api.urls'
APPEND_SLASH = False

AUTH_USER_MODEL = 'users.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'workspaces/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

FYLE_REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'apps.users.serializers.UserSerializer'
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'apps.workspaces.permissions.WorkspacePermissions'
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'fyle_rest_auth.authentication.FyleJWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100
}

WSGI_APPLICATION = 'fyle_netsuite_api.wsgi.application'

SERVICE_NAME = os.environ.get('SERVICE_NAME')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '{levelname} %s {asctime} {name} {worker_id} {message}' % SERVICE_NAME, 'style': '{'
        },
        'verbose': {
            'format': '{levelname} %s {asctime} {module} {message} ' % SERVICE_NAME, 'style': '{'
        },
        'requests': {
            'format': 'request {levelname} %s {asctime} {message}' % SERVICE_NAME, 'style': '{'
        }
    },
    'filters': {
        'worker_id': {
            '()': WorkerIDFilter,
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'filters': ['worker_id'],
        },
        'request_logs': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'requests'
        },
        'debug_logs': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.request': {'handlers': ['request_logs'], 'propagate': False},
    },
}

dictConfig(LOGGING)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'auth_cache',
    }
}

FYLE_REST_AUTH_SETTINGS = {
    'async_update_user': True
}

Q_CLUSTER = {
    'name': 'fyle_netsuite_api',
    # The number of tasks will be stored in django q tasks
    "save_limit": 100000,
    'workers': int(os.environ.get('NO_WORKERS', 4)),
    # How many tasks are kept in memory by a single cluster.
    # Helps balance the workload and the memory overhead of each individual cluster
    'queue_limit': 10,
    'cached': False,
    'orm': 'default',
    'ack_failures': True,
    'poll': 5,
    'max_attempts': 1,
    'attempt_count': 1,
    'retry': 14400,
    'timeout': 900, # 15 mins
    'catch_up': False,
    # The number of tasks a worker will process before recycling.
    # Useful to release memory resources on a regular basis.
    'recycle': os.environ.get('DJANGO_Q_RECYCLE', 20),
    # The maximum resident set size in kilobytes before a worker will recycle and release resources.
    # Useful for limiting memory usage.
    'max_rss': 50000, # 50mb
    'ALT_CLUSTERS': {
        'import': {
            'retry': 14400,
            'timeout': 1200, # 20 mins
        },
    }
}

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config()
}

DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True

DATABASES['cache_db'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': 'cache.db'
}

DATABASE_ROUTERS = ['fyle_netsuite_api.cache_router.CacheRouter']

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

# Fyle Settings
BRAND_ID = os.environ.get('BRAND_ID', 'fyle')
API_URL = os.environ.get('API_URL')
FYLE_TOKEN_URI = os.environ.get('FYLE_TOKEN_URI')
FYLE_CLIENT_ID = os.environ.get('FYLE_CLIENT_ID')
FYLE_CLIENT_SECRET = os.environ.get('FYLE_CLIENT_SECRET')
FYLE_BASE_URL = os.environ.get('FYLE_BASE_URL')
FYLE_APP_URL = os.environ.get('APP_URL')
FYLE_EXPENSE_URL = os.environ.get('FYLE_APP_URL')
INTEGRATIONS_APP_URL = os.environ.get('INTEGRATIONS_APP_URL')

# Netsuite Settings
NS_CONSUMER_KEY = os.environ.get('NS_CONSUMER_KEY')
NS_CONSUMER_SECRET = os.environ.get('NS_CONSUMER_SECRET')
SENDGRID_API_KEY = os.environ.get('SENDGRID_KEY')
EMAIL = os.environ.get('SENDGRID_EMAIL')
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
E2E_TESTS_CLIENT_SECRET = os.environ.get('E2E_TESTS_CLIENT_SECRET')
INTEGRATIONS_SETTINGS_API = os.environ.get('INTEGRATIONS_SETTINGS_API')
NETSUITE_INTEGRATION_APP_URL = os.environ.get('NETSUITE_INTEGRATION_APP_URL')

CACHE_EXPIRY = 3600

CORS_ORIGIN_ALLOW_ALL = True

# Sentry
Sentry.init()

CORS_ALLOW_HEADERS = [
    'sentry-trace',
    'authorization',
    'content-type'
]

# Toggle sandbox mode (when running in DEBUG mode)
SENDGRID_SANDBOX_MODE_IN_DEBUG=False

# echo to stdout or any other file-like object that is passed to the backend via the stream kwarg.
SENDGRID_ECHO_TO_STDOUT=True
