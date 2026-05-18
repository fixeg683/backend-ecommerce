from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
import requests
import base64
from datetime import datetime

from .mpesa_utils import get_access_token
from .models import Order, OrderItem, Product
from .serializers import OrderSerializer, ProductSerializer


# -----------------------------------
# HOME API
# -----------------------------------

@api_view(['GET'])
def api_home(request):
    return Response({
        "message": "Backend API running successfully"
    })


# -----------------------------------
# REGISTER (NEW)
# -----------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response(
            {"detail": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"detail": "A user with that username already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if email and User.objects.filter(email=email).exists():
        return Response(
            {"detail": "A user with that email already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )

    return Response(
        {"detail": "Account created successfully.", "username": user.username},
        status=status.HTTP_201_CREATED
    )


# -----------------------------------
# PRODUCTS (NEW)
# -----------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def product_list(request):
    products = Product.objects.select_related('category').all()
    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, pk):
    try:
        product = Product.objects.select_related('category').get(pk=pk)
    except Product.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = ProductSerializer(product, context={'request': request})
    return Response(serializer.data)


# -----------------------------------
# INITIATE PAYMENT  (replaces /payment/initiate/)
# also registered as /pay/ for frontend compatibility
# -----------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    try:
        phone = request.data.get("phone")
        amount = request.data.get("amount", 1)
        product_ids = request.data.get("product_ids", [])

        if not phone:
            return Response(
                {"success": False, "message": "Phone number required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        access_token, err = get_access_token()
        if not access_token:
            return Response(
                {"success": False, "message": err},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
            "Amount": int(amount),
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
            checkout_id = data.get("CheckoutRequestID")

            # Create a pending order linked to the authenticated user
            if product_ids:
                order = Order.objects.create(
                    user=request.user,
                    total_amount=amount,
                    phone=phone,
                    checkout_request_id=checkout_id,
                    status='Pending',
                    is_paid=False,
                )
                for pid in product_ids:
                    try:
                        product = Product.objects.get(pk=pid)
                        OrderItem.objects.create(order=order, product=product)
                    except Product.DoesNotExist:
                        pass

            return Response({
                "success": True,
                "CheckoutRequestID": checkout_id,
                "checkout_id": checkout_id,
                "message": "STK Push sent successfully"
            })

        return Response(
            {"success": False, "message": data},
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        return Response(
            {"success": False, "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# -----------------------------------
# VERIFY PAYMENT
# -----------------------------------

@api_view(['POST'])
def verify_payment(request):
    try:
        # Accept both key names for compatibility
        checkout_id = (
            request.data.get("checkout_request_id") or
            request.data.get("checkout_id")
        )

        if not checkout_id:
            return Response(
                {"success": False, "message": "Checkout ID missing"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(checkout_request_id=checkout_id)
        except Order.DoesNotExist:
            return Response({"success": False, "confirmed": False, "message": "Order not found"})

        if order.is_paid:
            return Response({"success": True, "confirmed": True, "message": "Payment confirmed"})

        # Not yet confirmed — callback hasn't fired
        return Response({"success": False, "confirmed": False, "message": "Payment pending"})

    except Exception as e:
        return Response(
            {"success": False, "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# -----------------------------------
# M-PESA CALLBACK
# -----------------------------------

@api_view(['POST'])
def mpesa_callback(request):
    try:
        data = request.data
        print("M-PESA CALLBACK:", data)

        # Parse callback body
        body = data.get('Body', {})
        stk = body.get('stkCallback', {})
        result_code = stk.get('ResultCode')
        checkout_id = stk.get('CheckoutRequestID')

        if checkout_id and result_code == 0:
            try:
                order = Order.objects.get(checkout_request_id=checkout_id)
                order.is_paid = True
                order.status = 'Completed'
                order.save()
                # Mark all order items as purchased
                order.items.update(purchased=True)
            except Order.DoesNotExist:
                pass

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        return Response({"ResultCode": 1, "ResultDesc": str(e)})


# -----------------------------------
# CHECK DOWNLOAD ACCESS
# -----------------------------------

@api_view(['GET'])
def check_download_access(request):
    unlocked = request.query_params.get("unlocked")
    if unlocked == "true":
        return Response({"success": True, "downloads_unlocked": True})
    return Response({"success": False, "downloads_unlocked": False})


# -----------------------------------
# DOWNLOAD FILE
# -----------------------------------

@api_view(['GET'])
def download_file(request):
    unlocked = request.query_params.get("unlocked")
    if unlocked != "true":
        return Response(
            {"success": False, "message": "Payment required"},
            status=status.HTTP_403_FORBIDDEN
        )
    return Response({"success": True, "file_url": "https://example.com/file.zip"})


# -----------------------------------
# M-PESA HEALTH CHECK
# -----------------------------------

@api_view(['GET'])
def mpesa_health(request):
    token, err = get_access_token()
    if token:
        return Response({"status": "healthy", "message": "M-Pesa credentials are valid and working."})
    return Response(
        {"status": "unhealthy", "message": err},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


# -----------------------------------
# MY ORDERS
# -----------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    try:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {"success": False, "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )