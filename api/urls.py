from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet, OrderViewSet
from . import views

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls)),

    # AUTH
    path('register/', views.register_user),
    path('users/me/', views.current_user),

    # DOWNLOADS
    path('download/<int:product_id>/', views.download_product),
]
