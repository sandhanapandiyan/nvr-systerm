"""
Django settings for NVR Project - Optimized for Performance

Enhanced with Django REST Framework, Channels (WebSocket), 
Redis Caching, and NVR-specific configurations.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# NVR-specific directories
RECORDINGS_DIR = BASE_DIR.parent / 'recordings'
EXPORTS_DIR = BASE_DIR.parent / 'exports'
STATIC_ROOT = BASE_DIR.parent / 'static_collected'

# Create directories if they don't exist
RECORDINGS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# Quick-start development settings
SECRET_KEY = 'django-insecure-)%_8of82c)j7+(*cz@@(1yy@#$*4*ewa(v*ftildx!2kazw2in'
DEBUG = True
ALLOWED_HOSTS = ['*']  # Configure for production


# Application definition
INSTALLED_APPS = [
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # NVR apps
    'cameras.apps.CamerasConfig',
    'recordings.apps.RecordingsConfig',
    'streaming.apps.StreamingConfig',
    'playback.apps.PlaybackConfig',
    'accounts.apps.AccountsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nvr_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Django templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cameras.context_processors.camera_context',  # Add camera counts
            ],
        },
    },
]

# WSGI application
WSGI_APPLICATION = 'nvr_project.wsgi.application'

# Database - Using SQLite with optimizations
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'data' / 'nvr_django.db',
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# Ensure data directory exists
(BASE_DIR.parent / 'data').mkdir(exist_ok=True)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # Adjust to your timezone
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR.parent / 'static']

# Media files
MEDIA_URL = '/media/'
# Point explicitly to the recordings folder on Desktop
MEDIA_ROOT = Path.home() / 'Desktop' / 'NVR_Recordings'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# DJANGO REST FRAMEWORK
# ============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# ============================================================================
# CORS SETTINGS - Allow frontend to access API
# ============================================================================
CORS_ALLOW_ALL_ORIGINS = True  # For development, restrict in production
CORS_ALLOW_CREDENTIALS = True

# ============================================================================
# DJANGO CHANNELS - WebSocket Configuration
# ============================================================================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Fallback to in-memory channel layer if Redis is not available
try:
    import redis
    r = redis.Redis(host='127.0.0.1', port=6379)
    r.ping()
except:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer'
        }
    }

# ============================================================================
# CACHING - Redis for frame caching (optional but recommended)
# ============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'nvr',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Fallback to local memory cache if Redis is not available
try:
    import redis
    r = redis.Redis(host='127.0.0.1', port=6379)
    r.ping()
except:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'nvr-cache',
        }
    }

# ============================================================================
# CELERY CONFIGURATION (for background tasks)
# ============================================================================
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ============================================================================
# NVR SPECIFIC SETTINGS
# ============================================================================
NVR_SETTINGS = {
    'SEGMENT_DURATION': 300,  # 5 minutes per recording segment
    'MAX_RETENTION_DAYS': 7,  # Keep recordings for 7 days
    'FRAME_CACHE_TIMEOUT': 30,  # Cache frames for 30 seconds
    'STREAM_TIMEOUT': 10,  # Stream connection timeout in seconds
    'MAX_RECONNECT_ATTEMPTS': 5,
    'RECONNECT_DELAY': 5,
}

# ============================================================================
# LOGGING
# ============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR.parent / 'logs' / 'django_nvr.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'cameras': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
        'recordings': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    },
}

# Create logs directory
(BASE_DIR.parent / 'logs').mkdir(exist_ok=True)

# ============================================================================
# AUTHENTICATION
# ============================================================================
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login'
