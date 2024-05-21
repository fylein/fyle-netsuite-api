import sys
import os

import dj_database_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

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
    'django_q'
]

MIDDLEWARE = [
    'fyle_netsuite_api.logging_middleware.ErrorHandlerMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'corsheaders.middleware.CorsPostCsrfMiddleware',
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
        'DIRS': [],
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
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '{levelname} %s {asctime} {module} {message} ' % SERVICE_NAME,
            'style': '{',
        },
        'requests': {
            'format': 'request {levelname} %s {asctime} {message}' % SERVICE_NAME,
            'style': '{'
        }
    },
    'handlers': {
        'debug_logs': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose'
        },
        'request_logs': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'requests'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['request_logs'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['request_logs'],
            'propagate': False
        },
        'fyle_netsuite_api': {
            'handlers': ['debug_logs'],
            'level': 'ERROR',
            'propagate': False
        },
        'apps': {
            'handlers': ['debug_logs'],
            'level': 'ERROR',
            'propagate': False
        },
        'django_q': {
            'handlers': ['debug_logs'],
            'level': 'INFO',
            'propagate': True
        },
        'fyle_integrations_imports': {
            'handlers': ['debug_logs'],
            'level': 'INFO',
            'propagate': True
        }
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'auth_cache',
    }
}

Q_CLUSTER = {
    'name': 'fyle_netsuite_api',
    'save_limit': 0,
    'workers': int(os.environ.get('NO_WORKERS', 4)),
    # How many tasks are kept in memory by a single cluster.
    # Helps balance the workload and the memory overhead of each individual cluster
    'queue_limit': 10,
    'cached': False,
    'orm': 'default',
    'ack_failures': True,
    'poll': 1,
    'max_attempts': 1,
    'attempt_count': 1,
    'retry': 14400,
    'timeout': 900, # 15 mins
    'catch_up': False,
    # The number of tasks a worker will process before recycling.
    # Useful to release memory resources on a regular basis.
    'recycle': 20,
    # The maximum resident set size in kilobytes before a worker will recycle and release resources.
    # Useful for limiting memory usage.
    'max_rss': 50000, # 50mb
    'ALT_CLUSTERS': {
         'import': {
            'retry': 14400,
            'timeout': 3600
        },
    }
}

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
if os.environ.get('DATABASE_URL', ''):
    DATABASES = {
        'default': dj_database_url.config()
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'OPTIONS': {
                'options': '-c search_path={0}'.format(os.environ.get('DB_SCHEMA'))
            },
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT'),
        }
    }

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

CACHE_EXPIRY = 3600

CORS_ORIGIN_ALLOW_ALL = True

"""
------------------------------------------ Test Settings ----------------------------------------------------
"""

# Fyle Settings
BRAND_ID = os.environ.get('BRAND_ID', 'fyle')
API_URL = os.environ.get('API_URL')
FYLE_TOKEN_URI = os.environ.get('FYLE_TOKEN_URI')
FYLE_CLIENT_ID = os.environ.get('FYLE_CLIENT_ID')
FYLE_CLIENT_SECRET = os.environ.get('FYLE_CLIENT_SECRET')
FYLE_REFRESH_TOKEN = os.environ.get('FYLE_REFRESH_TOKEN')
FYLE_BASE_URL = os.environ.get('FYLE_BASE_URL')
FYLE_APP_URL = os.environ.get('APP_URL')
FYLE_EXPENSE_URL = os.environ.get('FYLE_APP_URL')
INTEGRATIONS_SETTINGS_API = os.environ.get('INTEGRATIONS_SETTINGS_API')
NETSUITE_INTEGRATION_APP_URL = os.environ.get('NETSUITE_INTEGRATION_APP_URL')
INTEGRATIONS_APP_URL = os.environ.get('INTEGRATIONS_APP_URL')

# Netsuite Settings
NS_ACCOUNT_ID = 'sdfghj'
NS_TOKEN_ID = 'sdfghj'
NS_TOKEN_SECRET = 'sdfghj'
NS_CONSUMER_KEY = 'sdfghjk'
NS_CONSUMER_SECRET = 'sdfghjkl'
SENDGRID_API_KEY = os.environ.get('SENDGRID_KEY')
EMAIL = os.environ.get('SENDGRID_EMAIL')
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'


CACHE_EXPIRY = 3600

CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADERS = [
    'sentry-trace',
    'authorization',
    'content-type'
]

# Toggle sandbox mode (when running in DEBUG mode)
SENDGRID_SANDBOX_MODE_IN_DEBUG=False

# echo to stdout or any other file-like object that is passed to the backend via the stream kwarg.
SENDGRID_ECHO_TO_STDOUT=True
