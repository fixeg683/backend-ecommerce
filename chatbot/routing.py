from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/chatbot/(?P<session_key>[^/]+)/$', ChatConsumer.as_asgi()),
]
