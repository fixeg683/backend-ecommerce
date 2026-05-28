import os
from pathlib import Path
import dj_database_url
import cloudinary
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'unsafe-secret-key')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
_default_hosts = 'localhost,127.0.0.1,backend-ecommerce-3-2hqt.onrender.com'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', _default_hosts).split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'cloudinary',
    'cloudinary_storage',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'

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

# Normalize DATABASE_URL: Supabase dashboard sometimes shows an https:// URL
# but dj-database-url requires postgresql://
_db_url = os.environ.get('DATABASE_URL', '')
if _db_url.startswith('https://'):
    _db_url = _db_url.replace('https://', 'postgresql://', 1)

DATABASES = {
    'default': dj_database_url.config(
        default=_db_url,
        conn_max_age=600,
        ssl_require=True
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
if os.environ.get('VERCEL'):
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get("CLOUDINARY_CLOUD_NAME"),
    'API_KEY': os.environ.get("CLOUDINARY_API_KEY"),
    'API_SECRET': os.environ.get("CLOUDINARY_API_SECRET"),
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CORS_ALLOW_ALL_ORIGINS = False
_extra_origins = os.environ.get('CORS_ALLOWED_ORIGINS_EXTRA', '')
CORS_ALLOWED_ORIGINS = [
    "https://nexusapp-five.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
] + ([o.strip() for o in _extra_origins.split(',')] if _extra_origins else [])

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
    "accept",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------
# M-PESA
# -------------------------
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', 'PDnJ7OUF6DKvOX3dATyhoBlvyhyCpu4AFrtGxO8pAEiPFiMU')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', 'C4ry1pHCrTALwU9C2v1fQ4ytWRQvhAadNzqAW8kQHDdmQ272Bls98EsAQ9RwaQjh')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '4053577')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', '0841b9e4576d951d18a5c44078cdcda2b6e3265f89493109b6afc409865d7315')
BASE_URL = os.environ.get('BASE_URL', 'https://backend-ecommerce-3-2hqt.onrender.com')

# -------------------------
# LOGGING
# -------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# =========================
# LARGE FILE UPLOAD LIMITS
# =========================

# Django: allow up to 4 GB in a single request body
DATA_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024 * 1024   # 4 GB in bytes

# Django: allow files up to 4 GB on disk (in-memory threshold: keep at default 2.5 MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024            # 2.5 MB — stream to disk above this

# No limit on number of POST parameters (not relevant here but avoids surprises)
DATA_UPLOAD_MAX_NUMBER_FIELDS = None