from django.urls import path
from .views import verify_payment, check_access, download_product

urlpatterns = [
    path('verify-payment/', verify_payment),
    path('check-access/<int:product_id>/', check_access),
    path('download/<int:product_id>/', download_product),
]