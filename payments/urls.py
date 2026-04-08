from django.urls import path
from . import views

urlpatterns = [
    path('pay/', views.initiate_payment, name='initiate_payment'),
    path('payments/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('my-paid-products/', views.my_downloads, name='my_downloads'),
]