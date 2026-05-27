from django.urls import path
from django.http import JsonResponse

from .views import (
    RegisterView,
    login_user,
    get_products,
    get_product,
    create_order,
    verify_payment,
    mpesa_callback,
    user_downloads,
    user_orders,
    download_product,
    emergency_admin_reset,
)


def api_root(request):
    return JsonResponse({
        "message": "Ecommerce API is running",
        "endpoints": {
            "register": "/api/register/",
            "login": "/api/login/",
            "token": "/api/token/",
            "products": "/api/products/",
            "create_order": "/api/create-order/",
            "orders": "/api/orders/",
            "payment_verify": "/api/payment/verify/",
            "downloads": "/api/downloads/",
        }
    })


urlpatterns = [

    # API ROOT
    path('', api_root),

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
    path('payments/callback/', mpesa_callback),

    # =========================
    # DOWNLOADS
    # =========================

    path('downloads/', user_downloads),
    path('download/<int:product_id>/', download_product),

    # =========================
    # EMERGENCY ADMIN RESET (remove after use)
    # =========================
    path('reset-admin/', emergency_admin_reset),
]