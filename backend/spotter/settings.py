from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

def _env(name: str, default: str = '') -> str:
    val = os.environ.get(name, default)
    if isinstance(val, str):
        return val.strip().strip('"').strip("'")
    return val


def _env_bool(name: str, default: bool = False) -> bool:
    raw = str(_env(name, str(default))).lower()
    return raw in ('1', 'true', 'yes', 'on')


SECRET_KEY = _env('SECRET_KEY', 'django-insecure-dev-key-change-in-production-spotter-eld')

DEBUG = _env_bool('DEBUG', True)

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'trips',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'spotter.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'spotter.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _env('POSTGRES_DB', _env('PGDATABASE', 'spotter')),
        'USER': _env('POSTGRES_USER', _env('PGUSER', 'spotter')),
        'PASSWORD': _env('POSTGRES_PASSWORD', _env('PGPASSWORD', 'spotter')),
        'HOST': _env('POSTGRES_HOST', _env('PGHOST', 'localhost')),
        'PORT': _env('POSTGRES_PORT', _env('PGPORT', '5432')),
        'CONN_MAX_AGE': int(_env('POSTGRES_CONN_MAX_AGE', '60')),
        'OPTIONS': {
            'sslmode': _env('POSTGRES_SSLMODE', _env('PGSSLMODE', 'prefer')),
        },
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS - allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# LocationIQ settings
LOCATIONIQ_API_KEY = _env('LOCATIONIQ_API_KEY', _env('ORS_API_KEY', ''))
LOCATIONIQ_REGION = _env('LOCATIONIQ_REGION', 'us').lower()
