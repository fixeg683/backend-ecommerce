from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from api.views import api_root  # Import the new welcome view

urlpatterns = [
    # 1. Home / Root Path (Fixes the 404 on the main URL)
    path('', api_root, name='api-root'),

    # 2. Django Admin Login
    path('admin/', admin.site.urls),

    # 3. JWT Authentication Endpoints (For Login)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 4. Your Custom App Endpoints
    path('api/', include('api.urls')), 
]

# 5. Serve Media and Static Files (Only for Local Debugging)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)