import os
import hmac
import json
import logging

from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, get_user_model

from .models import Product, Order, OrderItem
from .serializers import ProductSerializer, RegisterSerializer
from .mpesa_utils import initiate_mpesa_payment, verify_mpesa_payment

logger = logging.getLogger(__name__)


# =========================
# AUTH
# =========================

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "User created successfully",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get('email')
    password = request.data.get('password')

    try:
        user_obj = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {"message": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    user = authenticate(username=user_obj.username, password=password)

    if user is not None:
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        })

    return Response(
        {"message": "Invalid credentials"},
        status=status.HTTP_401_UNAUTHORIZED
    )


# =========================
# PRODUCTS
# =========================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_products(request):
    products = Product.objects.all().order_by('-id')
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_product(request, pk):
    try:
        product = Product.objects.get(id=pk)
        return Response(ProductSerializer(product).data)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found"},
            status=status.HTTP_404_NOT_FOUND
        )


# =========================
# CREATE ORDER
# =========================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    phone_number = request.data.get('phone_number') or request.data.get('phone')
    amount = request.data.get('amount')
    product_ids = request.data.get('product_ids', [])

    if not phone_number:
        return Response({"error": "Phone number required"}, status=status.HTTP_400_BAD_REQUEST)

    if not amount:
        return Response({"error": "Amount required"}, status=status.HTTP_400_BAD_REQUEST)

    order = Order.objects.create(
        user=request.user,
        total_amount=amount,
        phone=phone_number,
        status='Pending',
    )

    for pid in product_ids:
        try:
            product = Product.objects.get(id=pid)
            OrderItem.objects.create(order=order, product=product)
        except Product.DoesNotExist:
            continue

    result = initiate_mpesa_payment(phone_number, amount, order.id)

    if isinstance(result, dict) and result.get('error'):
        order.delete()
        return Response({"error": result.get('error')}, status=status.HTTP_400_BAD_REQUEST)

    checkout_id = result.get('CheckoutRequestID') or result.get('checkoutRequestID')
    if checkout_id:
        order.checkout_request_id = checkout_id
        order.save()

    return Response({
        "message": "STK push sent",
        "order_id": order.id,
        "CheckoutRequestID": checkout_id,
    })


# =========================
# PAYMENT VERIFY
# =========================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    checkout_request_id = (
        request.data.get("checkout_request_id") or
        request.data.get("CheckoutRequestID")
    )

    if not checkout_request_id:
        return Response(
            {"success": False, "message": "checkout_request_id required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order = Order.objects.get(
            checkout_request_id=checkout_request_id,
            user=request.user,
        )
    except Order.DoesNotExist:
        return Response(
            {"success": False, "message": "Order not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Fast path — M-Pesa callback already confirmed this payment
    if order.is_paid:
        return Response({"success": True, "confirmed": True, "order_id": order.id})

    result = verify_mpesa_payment(checkout_request_id)

    if isinstance(result, dict) and result.get('error'):
        return Response(
            {"success": False, "message": result.get('error')},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if str(result.get('ResultCode', '')) == 'pending':
        return Response({"success": False, "confirmed": False, "message": "Payment still processing"})

    if str(result.get('ResultCode', '')) in ('0', '0.0'):
        order.is_paid = True
        order.status = 'Completed'
        order.save()
        return Response({"success": True, "confirmed": True, "order_id": order.id})

    return Response({
        "success": False,
        "confirmed": False,
        "message": result.get('ResultDesc', 'Payment not confirmed'),
    })


# =========================
# MPESA CALLBACK
# =========================

@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    try:
        data = request.data or json.loads(request.body)
        logger.info(f"M-Pesa Callback: {data}")

        stk_callback = data.get('Body', {}).get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        checkout_request_id = stk_callback.get('CheckoutRequestID')

        if not checkout_request_id:
            return Response({"ResultCode": 0, "ResultDesc": "Accepted, missing checkout ID"})

        try:
            order = Order.objects.get(checkout_request_id=checkout_request_id)
        except Order.DoesNotExist:
            return Response({"ResultCode": 0, "ResultDesc": "Accepted, order not found"})

        if str(result_code) in ('0', '0.0'):
            order.is_paid = True
            order.status = 'Completed'
        else:
            order.status = 'Failed'

        order.save()

    except Exception as e:
        logger.error(f"Callback error: {e}")

    # Always return 200 so Safaricom stops retrying
    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


# =========================
# DOWNLOAD PRODUCT
# =========================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_product(request, product_id):
    """Returns download URL for a product the user has paid for."""
    paid = OrderItem.objects.filter(
        order__user=request.user,
        order__is_paid=True,
        product__id=product_id,
    ).select_related('product').first()

    if not paid:
        return Response(
            {"detail": "Purchase this product to unlock the download."},
            status=status.HTTP_403_FORBIDDEN,
        )

    url = paid.product.downloadable_file
    if not url:
        return Response(
            {"detail": "No downloadable file attached to this product yet."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({"download_url": url})


# =========================
# USER DOWNLOADS
# =========================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_downloads(request):
    paid_orders = Order.objects.filter(user=request.user, is_paid=True)
    products = []

    for order in paid_orders:
        for item in OrderItem.objects.filter(order=order).select_related('product'):
            if item.product:
                products.append({
                    "id": item.product.id,
                    "name": item.product.name,
                    "price": item.product.price,
                    "image": item.product.image.url if item.product.image else "",
                    "downloadable_file": item.product.downloadable_file or "",
                })

    return Response({"paid": True, "products": products})


# =========================
# USER ORDERS
# =========================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_orders(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-id').prefetch_related('items__product')

    data = []
    for order in orders:
        data.append({
            "id": order.id,
            "is_paid": order.is_paid,
            "status": order.status,
            "total_amount": order.total_amount,
            "items": [
                {"product": {"id": item.product.id, "name": item.product.name}}
                for item in order.items.all() if item.product
            ],
        })

    return Response(data)


# =========================
# EMERGENCY ADMIN RESET
# Remove ADMIN_RESET_TOKEN env var after use
# =========================

@api_view(['GET'])
@permission_classes([AllowAny])
def emergency_admin_reset(request):
    provided = request.GET.get('token', '')
    secret   = os.environ.get('ADMIN_RESET_TOKEN', '')

    if not secret:
        return Response({'error': 'Reset not configured.'}, status=status.HTTP_403_FORBIDDEN)

    if not hmac.compare_digest(provided, secret):
        return Response({'error': 'Invalid token.'}, status=status.HTTP_403_FORBIDDEN)

    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Admin123!')

    UserModel = get_user_model()
    user, created = UserModel.objects.get_or_create(username=username)
    user.email        = email
    user.is_staff     = True
    user.is_superuser = True
    user.is_active    = True
    user.set_password(password)
    user.save()

    return Response({
        'status': 'ok',
        'action': 'created' if created else 'reset',
        'username': username,
        'note': 'Login at /admin/ — remove ADMIN_RESET_TOKEN env var after use.',
    })