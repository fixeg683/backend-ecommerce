import os
import hmac
import json
import logging
import time
import traceback
import secrets
import random
from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, get_user_model
from django.db import connections, transaction
from django.db.utils import OperationalError, InterfaceError
from django.utils import timezone

from .models import Product, Category, Order, OrderItem, EmailVerification
from .services.email_service import send_account_confirmation_email, send_verification_code_email
from .serializers import (
    ProductSerializer,
    CategorySerializer,
    OrderSerializer,
    UserSerializer,
)
from .mpesa_utils import initiate_mpesa_payment, verify_mpesa_payment

logger = logging.getLogger(__name__)

# -------------------------
# HEALTH CHECK
# -------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Lightweight health/readiness probe: GET /api/health/
      200 {"status": "ok", "database": "ok", "latency_ms": <float>}
      503 {"status": "error", "database": "unreachable", "detail": "<message>"}

    Runs a real query (not just ensure_connection()) so a pooler that
    accepts TCP but rejects the tenant/auth is still caught.
    """
    db_status = "ok"
    detail = None
    started = time.monotonic()

    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except (OperationalError, InterfaceError) as e:
        db_status = "unreachable"
        detail = str(e)
    except Exception as e:
        db_status = "error"
        detail = str(e)

    latency_ms = round((time.monotonic() - started) * 1000, 2)

    if db_status != "ok":
        logger.error("[HEALTH CHECK] database=%s detail=%s", db_status, detail)
        return Response(
            {"status": "error", "database": db_status, "detail": detail},
            status=503,
        )

    return Response(
        {"status": "ok", "database": "ok", "latency_ms": latency_ms},
        status=200,
    )

# -------------------------
# ROOT
# -------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    return Response({"message": "Welcome to the E-Space API", "status": "Running"})

# -------------------------
# VIEWSETS
# -------------------------

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error("[ProductViewSet.list ERROR] %s", traceback.format_exc())
            return Response({"error": "Failed to load products"}, status=500)

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            logger.error("[ProductViewSet.retrieve ERROR] %s", traceback.format_exc())
            return Response({"error": "Failed to load product"}, status=500)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)\
            .prefetch_related('items__product')\
            .order_by('-id')

    @action(detail=False, methods=['get'], url_path='my-orders')
    def my_orders(self, request):
        """Returns purchased products in flat structure for frontend."""
        orders = self.get_queryset().filter(is_paid=True)
        data = []
        for order in orders:
            for item in order.items.all():
                if item.purchased:
                    product = item.product
                    data.append({
                        "order_id": order.id,
                        "is_paid": order.is_paid,
                        "product": {
                            "id": product.id,
                            "name": product.name,
                            "description": product.description,
                            "price": str(product.price),
                            "image": product.image.url if product.image else None,
                        }
                    })
        return Response(data)

# -------------------------
# AUTH
# -------------------------

def _create_verification_code(user):
    verification, _ = EmailVerification.objects.get_or_create(user=user)
    code = verification.generate_code()
    return verification, code


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Create an inactive account and send a 6-digit verification code."""
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    username = request.data.get('username') or email

    if not email or not password:
        return Response(
            {"message": "Email and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {"message": "An account with this email already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"message": "An account with this username already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False,
            )
            verification, code = _create_verification_code(user)
            email_result = send_verification_code_email(
                to_email=user.email,
                user_name=user.first_name or user.username,
                code=code,
            )
    except Exception:
        logger.exception('Registration failed before verification email dispatch for email=%s username=%s', email, username)
        return Response(
            {'message': 'Registration failed. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if not email_result['success']:
        logger.error('Registration email could not be sent to %s: %s', user.email, email_result.get('error'))
        verification.delete()
        user.delete()
        return Response(
            {'message': 'Account created, but the verification code could not be sent. Please try again later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({
        "message": "Registration successful! Please check your email for the verification code.",
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code(request):
    email = request.data.get('email', '').strip()
    code = str(request.data.get('code', '')).strip()

    if not email or not code:
        return Response({"message": "Email and code are required."}, status=status.HTTP_400_BAD_REQUEST)

    verification = EmailVerification.objects.select_related('user').filter(user__email=email).first()
    if not verification or verification.code != code:
        return Response({"message": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)

    if not verification.expires_at or verification.expires_at <= timezone.now():
        return Response({"message": "Verification code has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

    user = verification.user
    user.is_active = True
    user.save(update_fields=['is_active'])
    verification.delete()

    return Response({'message': 'Account verified successfully! You can now log in.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_code(request):
    email = request.data.get('email', '').strip()
    if not email:
        return Response({"message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"message": "Account not found."}, status=status.HTTP_400_BAD_REQUEST)

    if user.is_active:
        return Response({"message": "This account is already verified."}, status=status.HTTP_400_BAD_REQUEST)

    verification, code = _create_verification_code(user)
    email_result = send_verification_code_email(
        to_email=user.email,
        user_name=user.first_name or user.username,
        code=code,
    )

    if not email_result['success']:
        logger.error('Verification code resent email failed for %s', user.email)
        return Response({"message": "Could not resend the verification code. Please try again later."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({"message": "A new verification code has been sent."})


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.query_params.get('token')
    if not token:
        return Response({'message': 'Token is missing.'}, status=status.HTTP_400_BAD_REQUEST)

    verification = EmailVerification.objects.select_related('user').filter(token=token).first()
    if not verification or not verification.expires_at or verification.expires_at <= timezone.now():
        return Response(
            {'message': 'Verification token is invalid or has expired.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = verification.user
    user.is_active = True
    user.save(update_fields=['is_active'])
    verification.delete()

    return Response({'message': 'Account verified successfully! You can now log in.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Return the authenticated user's profile."""
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
    })


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
    try:
        products = Product.objects.all().order_by('-id')
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error("[get_products ERROR] %s", traceback.format_exc())
        return Response({"error": "Failed to load products"}, status=500)

# -------------------------
# PAYMENTS
# -------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay(request):
    """
    Initiate M-Pesa STK Push.
    Expects: { phone, amount, product_ids: [...] }
    """
    try:
        phone = request.data.get('phone', '').strip()
        amount = request.data.get('amount')
        product_ids = request.data.get('product_ids', [])

        if not phone or amount is None:
            return Response({"error": "phone and amount are required"}, status=400)

        if not product_ids:
            return Response({"error": "product_ids cannot be empty"}, status=400)

        # Safely coerce amount to int
        try:
            amount_int = int(float(amount))
        except (TypeError, ValueError):
            return Response({"error": "Invalid amount value"}, status=400)

        if amount_int <= 0:
            return Response({"error": "Amount must be greater than 0"}, status=400)

        # Create a pending Order
        order = Order.objects.create(
            user=request.user,
            total_amount=amount_int,
            phone=phone,
            status='Pending'
        )

        # Attach products as OrderItems
        for pid in product_ids:
            try:
                product = Product.objects.get(id=pid)
                OrderItem.objects.get_or_create(order=order, product=product)
            except Product.DoesNotExist:
                pass

        # Fire STK Push
        result = initiate_mpesa_payment(phone, amount_int, order.id)

        if 'error' in result:
            order.status = 'Failed'
            order.save()
            return Response({"error": result['error']}, status=502)

        # Save CheckoutRequestID for polling / callback matching
        order.checkout_request_id = result.get('CheckoutRequestID')
        order.save()

        return Response(result, status=200)

    except Exception as e:
        logger.error("[PAY ERROR] %s", traceback.format_exc())
        return Response({"error": f"Server error: {str(e)}"}, status=500)


# -------------------------
# DOWNLOADS
# -------------------------

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

    if str(result.get('ResultCode', '')) == 'pending' or result.get('errorCode') == '500.001.1001':
        return Response({"success": False, "confirmed": False, "message": "Payment still processing"})

    if str(result.get('ResultCode', '')) in ('0', '0.0'):
        order.is_paid = True
        order.status = 'Completed'
        order.items.all().update(purchased=True)
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
            order.items.all().update(purchased=True)
        else:
            order.status = 'Failed'

        order.save()
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        logger.error("[CALLBACK ERROR] %s", traceback.format_exc())
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_downloads(request):
    """
    Returns all products the user has paid for, in the shape
    the frontend Downloads page expects: { products: [...] }.
    """
    try:
        items = (
            OrderItem.objects.filter(
                order__user=request.user,
                purchased=True,
            )
            .select_related('product')
            .distinct()
        )

        seen_ids = set()
        products = []
        for item in items:
            product = item.product
            if not product or product.id in seen_ids:
                continue
            seen_ids.add(product.id)
            products.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": str(product.price),
                "image": product.image.url if product.image else None,
                "product_type": product.product_type,
                "downloadable_file": (
                    product.download_url_override
                    or (product.file.url if product.file else None)
                ),
            })

        return Response({"products": products})

    except Exception as e:
        logger.error("[MY DOWNLOADS ERROR] %s", traceback.format_exc())
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_product(request, product_id):
    """
    Returns the Cloudinary download URL for a purchased product.
    Uses .filter().first() to avoid MultipleObjectsReturned crashes.
    """
    try:
        item = OrderItem.objects.filter(
            order__user=request.user,
            product_id=product_id,
            purchased=True
        ).select_related('product').first()

        if not item:
            return Response(
                {"error": "Purchase required to download this product"},
                status=403
            )

        product = item.product
        url = product.download_url_override or (product.file.url if product.file else None)

        if url:
            return Response({"download_url": url})

        return Response({"error": "No file available for this product"}, status=404)

    except Exception as e:
        logger.error("[DOWNLOAD ERROR] %s", traceback.format_exc())
        return Response({"error": f"Server error: {str(e)}"}, status=500)

# -------------------------
# PAID PRODUCT IDS
# -------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_paid_product_ids(request):
    """Returns a flat list of product IDs the user has purchased."""
    try:
        ids = list(
            OrderItem.objects.filter(
                order__user=request.user,
                purchased=True
            ).values_list('product_id', flat=True).distinct()
        )
        return Response(ids)
    except Exception as e:
        logger.error("[PAID IDS ERROR] %s", traceback.format_exc())
        return Response({"error": str(e)}, status=500)

# -------------------------
# ADMIN PASSWORD RESET
# -------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_admin(request):
    """
    One-time emergency admin password reset.
    Requires ADMIN_RESET_TOKEN env var to be set on Render.
    REMOVE the env var after use to disable this endpoint permanently.

    POST /api/reset-admin/
    { "token": "<ADMIN_RESET_TOKEN>", "new_password": "<your new password>" }
    """
    secret = os.environ.get('ADMIN_RESET_TOKEN', '').strip()

    if not secret:
        return Response(
            {"error": "This endpoint is disabled. Set ADMIN_RESET_TOKEN env var to enable it."},
            status=status.HTTP_403_FORBIDDEN,
        )

    token    = request.data.get('token', '').strip()
    new_pass = request.data.get('new_password', '').strip()

    if not hmac.compare_digest(token, secret):
        logger.warning("reset_admin: bad token attempt from %s", request.META.get('REMOTE_ADDR'))
        return Response({"error": "Invalid token."}, status=status.HTTP_403_FORBIDDEN)

    if len(new_pass) < 8:
        return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

    User = get_user_model()
    try:
        admin = User.objects.filter(is_superuser=True).order_by('id').first()
        if not admin:
            return Response({"error": "No superuser found."}, status=status.HTTP_404_NOT_FOUND)

        admin.set_password(new_pass)
        admin.is_staff = True
        admin.is_active = True
        admin.save()

        logger.info("reset_admin: password updated for user '%s'", admin.username)
        return Response({
            "success": True,
            "username": admin.username,
            "note": "Login at /admin/ — remove ADMIN_RESET_TOKEN env var after use.",
        })
    except Exception as e:
        logger.error("reset_admin error: %s", traceback.format_exc())
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)