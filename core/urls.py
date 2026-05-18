from django.urls import path
from .views import *

urlpatterns = [

    # -----------------------------------
    # API HOME
    # -----------------------------------
    path('', api_home, name='api-home'),

    # -----------------------------------
    # AUTH
    # -----------------------------------
    path('register/', register_user, name='register'),

    # -----------------------------------
    # PRODUCTS
    # -----------------------------------
    path('products/', product_list, name='product-list'),
    path('products/<int:pk>/', product_detail, name='product-detail'),

    # -----------------------------------
    # PAYMENT ROUTES
    # Legacy path kept for admin/testing; /pay/ added for frontend
    # -----------------------------------
    path('payment/initiate/', initiate_payment, name='initiate-payment'),
    path('pay/', initiate_payment, name='pay'),           # ← frontend calls this
    path('payment/verify/', verify_payment, name='verify-payment-legacy'),
    path('verify-payment/', verify_payment, name='verify-payment'),  # ← frontend calls this
    path('payment/callback/', mpesa_callback, name='mpesa-callback'),

    # -----------------------------------
    # DOWNLOAD ROUTES
    # -----------------------------------
    path('downloads/check/', check_download_access, name='check-download-access'),
    path('downloads/file/', download_file, name='download-file'),

    path('mpesa-health/', mpesa_health, name='mpesa-health'),

    # -----------------------------------
    # ORDERS
    # -----------------------------------
    path('orders/my-orders/', my_orders, name='my-orders'),
]