from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def home(request):
    return Response({
        'message': 'E-Commerce API is running 🚀',
        'endpoints': {
            'api': '/api/',
            'admin': '/admin/',
            'login': '/api/token/',
            'chatbot': '/api/chatbot/',
        },
    })

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/chatbot/webhooks/', include('chatbot.webhook_urls')),
    path('api/chatbot/', include('chatbot.urls')),
    path('api/', include('api.urls')),
]