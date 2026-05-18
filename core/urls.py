from django.contrib import admin
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def home(request):
    return Response({
        "message": "E-Commerce API is running 🚀",
        "endpoints": {
            "api": "/api/",
            "admin": "/admin/",
            "login": "/api/token/",
            "refresh": "/api/token/refresh/",
            "register": "/api/register/",
            "products": "/api/products/",
        }
    })


urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),          # ← includes api/urls.py ONLY, never core/urls.py
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]