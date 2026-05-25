from django.urls import path

from .views import (
    RegisterView,
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

    path('register/', RegisterView.as_view()),
    path('login/', login_user),

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