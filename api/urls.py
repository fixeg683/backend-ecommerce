from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # AUTH
    path('register/', views.register_user),
    path('users/me/', views.current_user),

    # PAYMENT
    path('pay/', views.initiate_payment),
    path('payments/callback/', views.mpesa_callback),

    # ORDERS
    path('orders/', views.my_orders),

    # DOWNLOAD SYSTEM (Alias fixed to resolve frontend 404)
    path('my-downloads/', views.my_downloads),
    path('my-paid-products/', views.my_downloads), # FIX: Frontend expects this URL
    path('download/<int:product_id>/', views.download_product),
]