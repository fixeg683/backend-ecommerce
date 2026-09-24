from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import EmailTokenObtainPairSerializer
from .views import (
    my_paid_product_ids,
    ProductViewSet,
    CategoryViewSet,
    OrderViewSet,
    api_root,
    health_check,
    register_user,
    verify_code,
    resend_code,
    verify_email,
    current_user,
    my_downloads,
    download_product,
    pay,
    verify_payment,
    mpesa_callback,
    reset_admin,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', api_root),
    path('health/', health_check, name='health-check'),

    # Auth
    path('register/', register_user, name='register'),
    path('verify-code/', verify_code, name='verify-code'),
    path('resend-code/', resend_code, name='resend-code'),
    path('verify-email/', verify_email, name='verify-email'),
    path('me/', current_user),
    path('reset-admin/', reset_admin, name='reset-admin'),

    # JWT — must live here inside api/urls.py; core/urls.py paths are shadowed by include('api.urls')
    path('token/', TokenObtainPairView.as_view(serializer_class=EmailTokenObtainPairSerializer), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

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