from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    CategoryViewSet,
    OrderViewSet,
    api_root,
    register_user,
    current_user,
    my_downloads,
    download_product
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', api_root),

    # ✅ ADD THIS (your missing endpoint)
    path('register/', register_user, name='register'),

    # optional but recommended
    path('me/', current_user),
    path('downloads/', my_downloads),
    path('download/<int:product_id>/', download_product),

    path('', include(router.urls)),
]
