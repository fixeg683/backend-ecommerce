import os
from pathlib import Path
from datetime import timedelta
from decouple import config
import dj_database_url

# ... Base Directory and Secret Key ...
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# ... Allowed Hosts ...
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok-free.app']

# --- Database Configuration ---
# This parses the DATABASE_URL from .env and adds SSL requirements
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Add explicit SSL options for PostgreSQL
DATABASES['default']['OPTIONS'] = {
    'sslmode': 'require',
}

# --- Rest Framework & JWT ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ... Rest of your settings (Middleware, Apps, etc.) ...