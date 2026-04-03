import os
import dj_database_url
from datetime import timedelta
from decouple import config
from pathlib import Path

# 1. BASE DIRECTORY
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. SECURITY
# Ensure these are set in your Render Environment Variables
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)

# 3. ALLOWED HOSTS
# Includes Render defaults and your specific backend URL
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
    
    # Your Apps
    'api', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Critical for Render static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Position is critical: Above CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls' 

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

# 5. DATABASE (Supabase Connection)
# This uses the DATABASE_URL from your Render environment variables
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Explicit SSL requirement for Supabase/PostgreSQL
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
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# 7. INTERNATIONALIZATION
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi' # Set to your local time zone
USE_I18N = True
USE_TZ = True

# 8. STATIC & MEDIA FILES
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Use WhiteNoise to serve static files efficiently on Render
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 9. CORS & CSRF (Crucial for Vercel Frontend)
# This solves the "Blocked by CORS policy" error you saw in the console
CORS_ALLOW_ALL_ORIGINS = True 

# If you want to be stricter later, uncomment and use:
# CORS_ALLOWED_ORIGINS = [
#     "https://ecommerce-frontend-7fcl.vercel.app",
# ]

CSRF_TRUSTED_ORIGINS = [
    'https://backend-ecommerce-3-href.onrender.com',
    'https://*.onrender.com',
    'https://ecommerce-frontend-7fcl.vercel.app'
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'