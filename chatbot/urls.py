from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.create_session, name='chatbot-create-session'),
    path('sessions/<int:session_id>/', views.session_history, name='chatbot-session-history'),
    path('sessions/<int:session_id>/messages/', views.send_message, name='chatbot-send-message'),
    path('leads/', views.capture_lead, name='chatbot-capture-lead'),
    path('track-view/', views.track_view, name='chatbot-track-view'),
    path('track-click/', views.track_click, name='chatbot-track-click'),
]
