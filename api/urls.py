from django.urls import path
from . import views

urlpatterns = [
    # Product/Ecommerce Endpoints
    path('products/', views.ProductList.as_view(), name='product-list'),
    path('products/<int:pk>/', views.ProductDetail.as_view(), name='product-detail'),
    
    # M-Pesa Payment Endpoints
    path('payments/initiate/', views.InitiatePaymentView.as_view(), name='initiate-payment'),
    path('payments/callback/', views.MpesaCallbackView.as_view(), name='mpesa-callback'),
    path('payments/query/<str:checkout_id>/', views.QueryPaymentStatusView.as_view(), name='query-payment'),
]