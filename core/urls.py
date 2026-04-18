from django.contrib import admin
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# ✅ ROOT VIEW
@api_view(['GET'])
def home(request):
    return Response({
        "message": "E-Commerce API is running 🚀",
        "endpoints": {
            "api": "/api/",
            "admin": "/admin/",
            "login": "/api/token/",
        }
    })

urlpatterns = [
    # ✅ FIX HERE
    path('', home),

    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),

    # JWT
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]
