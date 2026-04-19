from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    my_paid_product_ids,
    ProductViewSet,
    CategoryViewSet,
    OrderViewSet,
    api_root,
    register_user,
    current_user,
    my_downloads,
    download_product,
    pay,
    verify_payment,
    mpesa_callback,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', api_root),

    # Auth
    path('register/', register_user, name='register'),
    path('me/', current_user),

    # Downloads
    path('downloads/', my_downloads),
    path('download/<int:product_id>/', download_product),

    # Payments
    path('pay/', pay, name='pay'),
    path('verify-payment/', verify_payment, name='verify-payment'),
    path('payments/callback/', mpesa_callback, name='mpesa-callback'),
    path('my-paid-products/', my_paid_product_ids, name='my-paid-products'),

    # Router (products, categories, orders)
    path('', include(router.urls)),
]
