from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.chatbot_root, name='chatbot_root'),
    re_path(r'^sessions/?$', views.create_session, name='chatbot-create-session'),
    re_path(r'^sessions/(?P<session_id>\d+)/?$', views.session_history, name='chatbot-session-history'),
    re_path(r'^sessions/(?P<session_id>\d+)/messages/?$', views.send_message, name='chatbot-send-message'),
    re_path(r'^leads/?$', views.capture_lead, name='chatbot-capture-lead'),
    re_path(r'^track-view/?$', views.track_view, name='chatbot-track-view'),
    re_path(r'^track-click/?$', views.track_click, name='chatbot-track-click'),
]
