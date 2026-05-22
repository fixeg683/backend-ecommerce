from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from .views import (
    register_user,
    login_user,
    get_products,
    get_product,
    create_order,
    verify_payment,
    user_downloads,
    user_orders,
)

urlpatterns = [

    # =========================
    # AUTH
    # =========================

    path('register/', register_user),
    path('login/', login_user),
    path('token/refresh/', TokenRefreshView.as_view()),

    # =========================
    # PRODUCTS
    # =========================

    path('products/', get_products),
    path('products/<int:pk>/', get_product),

    # =========================
    # ORDERS
    # =========================

    path('create-order/', create_order),
    path('orders/', user_orders),

    # =========================
    # PAYMENT
    # =========================

    path('payment/verify/', verify_payment),

    # =========================
    # DOWNLOADS
    # =========================

    path('downloads/', user_downloads),
]