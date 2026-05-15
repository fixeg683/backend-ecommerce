from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import JsonResponse
import requests
import base64
from datetime import datetime

from .mpesa_utils import get_mpesa_access_token


# -----------------------------------
# HOME API
# -----------------------------------

@api_view(['GET'])
def api_home(request):

    return Response({
        "message": "Backend API running successfully"
    })


# -----------------------------------
# INITIATE PAYMENT
# -----------------------------------

@api_view(['POST'])
def initiate_payment(request):

    try:

        phone = request.data.get("phone")
        amount = request.data.get("amount", 1)

        if not phone:

            return Response({
                "success": False,
                "message": "Phone number required"
            }, status=status.HTTP_400_BAD_REQUEST)

        access_token = get_mpesa_access_token()

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        business_shortcode = settings.MPESA_SHORTCODE
        passkey = settings.MPESA_PASSKEY

        password = base64.b64encode(
            f"{business_shortcode}{passkey}{timestamp}".encode()
        ).decode()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": business_shortcode,
            "PhoneNumber": phone,
            "CallBackURL": f"{settings.BASE_URL}/api/payment/callback/",
            "AccountReference": "NeuronStore",
            "TransactionDesc": "Digital Product Purchase"
        }

        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers
        )

        data = response.json()

        if data.get("ResponseCode") == "0":

            return Response({
                "success": True,
                "checkout_id": data.get("CheckoutRequestID"),
                "message": "STK Push sent successfully"
            })

        return Response({
            "success": False,
            "message": data
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:

        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------------------
# VERIFY PAYMENT
# -----------------------------------

@api_view(['POST'])
def verify_payment(request):

    try:

        checkout_id = request.data.get("checkout_id")

        if not checkout_id:

            return Response({
                "success": False,
                "message": "Checkout ID missing"
            }, status=status.HTTP_400_BAD_REQUEST)

        # TEMPORARY SUCCESS RESPONSE
        # Replace with actual DB verification later

        return Response({
            "success": True,
            "message": "Payment verified successfully",
            "downloads_unlocked": True
        })

    except Exception as e:

        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------------------
# M-PESA CALLBACK
# -----------------------------------

@api_view(['POST'])
def mpesa_callback(request):

    try:

        data = request.data

        print("M-PESA CALLBACK:")
        print(data)

        return Response({
            "ResultCode": 0,
            "ResultDesc": "Accepted"
        })

    except Exception as e:

        return Response({
            "ResultCode": 1,
            "ResultDesc": str(e)
        })


# -----------------------------------
# CHECK DOWNLOAD ACCESS
# -----------------------------------

@api_view(['GET'])
def check_download_access(request):

    unlocked = request.query_params.get("unlocked")

    if unlocked == "true":

        return Response({
            "success": True,
            "downloads_unlocked": True
        })

    return Response({
        "success": False,
        "downloads_unlocked": False
    })


# -----------------------------------
# DOWNLOAD FILE
# -----------------------------------

@api_view(['GET'])
def download_file(request):

    unlocked = request.query_params.get("unlocked")

    if unlocked != "true":

        return Response({
            "success": False,
            "message": "Payment required"
        }, status=status.HTTP_403_FORBIDDEN)

    return Response({
        "success": True,
        "file_url": "https://example.com/file.zip"
    })