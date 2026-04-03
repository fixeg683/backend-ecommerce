from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.register_user, name='register'),
    path('users/me/', views.current_user, name='current-user'),  # ← new
    path('pay/', views.initiate_payment, name='pay'),
    path('payments/callback/', views.mpesa_callback, name='callback'),
    path('orders/', views.my_orders, name='my-orders'),
]