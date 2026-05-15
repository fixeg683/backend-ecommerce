from django.urls import path
from .views import *

urlpatterns = [

    # -----------------------------------
    # API HOME
    # -----------------------------------

    path(
        '',
        api_home,
        name='api-home'
    ),

    # -----------------------------------
    # PAYMENT ROUTES
    # -----------------------------------

    path(
        'payment/initiate/',
        initiate_payment,
        name='initiate-payment'
    ),

    path(
        'payment/verify/',
        verify_payment,
        name='verify-payment'
    ),

    path(
        'payment/callback/',
        mpesa_callback,
        name='mpesa-callback'
    ),

    # -----------------------------------
    # DOWNLOAD ROUTES
    # -----------------------------------

    path(
        'downloads/check/',
        check_download_access,
        name='check-download-access'
    ),

    path(
        'downloads/file/',
        download_file,
        name='download-file'
    ),

    path(
        'mpesa-health/',
        mpesa_health,
        name='mpesa-health'
    ),
]