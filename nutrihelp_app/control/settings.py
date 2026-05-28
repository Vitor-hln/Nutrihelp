from decouple import config, Csv
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# CRITICO: sem default — container falha com mensagem clara (D-09)
SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:3600', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # DRF
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    # API docs (usada na Phase 7, mas app registrada desde Phase 1)
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # DEVE ficar logo apos SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'control.urls'

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

WSGI_APPLICATION = 'control.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST', default='nutrihelp_postgres'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    }
}

# Celery — namespace CELERY_ no settings (pattern de RESEARCH.md)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://nutrihelp_redis:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://nutrihelp_redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'

# JWT — valores do CLAUDE.md (mais conservadores que o guia)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# DRF — preparado para fases seguintes
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Static files (whitenoise)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Variaveis de LLM (usadas a partir da Phase 5)
LLM_PROVIDER = config('LLM_PROVIDER', default='ollama')
OLLAMA_BASE_URL = config('OLLAMA_BASE_URL', default='http://nutrihelp_ollama:11434')
OLLAMA_MODEL = config('OLLAMA_MODEL', default='llama3.1:8b-instruct-q4_K_M')
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Vector store (usado a partir da Phase 4/5)
VECTOR_STORE = config('VECTOR_STORE', default='chroma')
CHROMA_HOST = config('CHROMA_HOST', default='nutrihelp_chromadb')
CHROMA_PORT = config('CHROMA_PORT', default=8000, cast=int)

# Internacionalizacao
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
