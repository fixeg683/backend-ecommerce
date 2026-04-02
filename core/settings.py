import os
import dj_database_url
from datetime import timedelta
from decouple import config
from pathlib import Path

# 1. BASE DIRECTORY
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. SECURITY
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# 3. ALLOWED HOSTS (Added Render wildcards)
ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1', 
    '.onrender.com', 
    'backend-ecommerce-3-href.onrender.com'
]

# 4. APP DEFINITION
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third Party Apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Your Apps (Ensure these match your folder names)
    'api', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # For static files on Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Must be above CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls' # Ensure 'core' matches your project folder name

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

WSGI_APPLICATION = 'core.wsgi.application'

# 5. DATABASE (Supabase via dj-database-url)
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Explicit SSL for Supabase
DATABASES['default']['OPTIONS'] = {
    'sslmode': 'require',
}

# 6. AUTHENTICATION & JWT
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# 7. INTERNATIONALIZATION
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# 8. STATIC & MEDIA FILES (WhiteNoise Setup)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 9. CORS & CSRF (For Vercel Frontend)
CORS_ALLOW_ALL_ORIGINS = True # Change to specific Vercel URL in production
CSRF_TRUSTED_ORIGINS = [
    'https://backend-ecommerce-3-href.onrender.com',
    'https://*.onrender.com'
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'