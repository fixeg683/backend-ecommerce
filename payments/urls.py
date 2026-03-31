from django.urls import path
from api.views import initiate_payment, mpesa_callback

urlpatterns = [
    path('initiate/', initiate_payment, name='mpesa-initiate'),
    path('callback/', mpesa_callback, name='mpesa-callback'),
]