import os
import dj_database_url
from decouple import config
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

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