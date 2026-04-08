from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet
from . import views

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
    # AUTH
    path('register/', views.register_user),
    path('users/me/', views.current_user),
    # PAYMENT
    path('pay/', views.initiate_payment),
    path('payments/callback/', views.mpesa_callback),
    path('verify-payment/', views.verify_payment),  # ← ADD THIS
    # ORDERS
    path('orders/', views.my_orders),
    # DOWNLOADS
    path('my-downloads/', views.my_downloads),
    path('my-paid-products/', views.my_downloads),
    path('download/<int:product_id>/', views.download_product),
]