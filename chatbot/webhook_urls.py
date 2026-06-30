from django.urls import path
from .webhook_views import whatsapp_webhook, instagram_webhook

urlpatterns = [
    path('whatsapp/', whatsapp_webhook, name='chatbot-whatsapp-webhook'),
    path('instagram/', instagram_webhook, name='chatbot-instagram-webhook'),
]
