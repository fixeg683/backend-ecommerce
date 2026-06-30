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
from .models import Product, Category, Order, OrderItem
from .serializers import (
    ProductSerializer,
    CategorySerializer,
    OrderSerializer,
    UserSerializer
)
from .mpesa_utils import initiate_mpesa_payment, verify_mpesa_payment
import traceback

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
        print(f"[PAY ERROR] {traceback.format_exc()}")
        return Response({"error": f"Server error: {str(e)}"}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """
    Poll M-Pesa for STK Push status.
    Expects: { checkout_request_id }
    """
    try:
        checkout_request_id = request.data.get('checkout_request_id', '').strip()
        if not checkout_request_id:
            return Response({"error": "checkout_request_id is required"}, status=400)

        result = verify_mpesa_payment(checkout_request_id)

        # Mark order paid on confirmed result
        if str(result.get('ResultCode', '')) == '0':
            try:
                order = Order.objects.get(
                    checkout_request_id=checkout_request_id,
                    user=request.user
                )
                order.is_paid = True
                order.status = 'Completed'
                order.save()
                order.items.all().update(purchased=True)
            except Order.DoesNotExist:
                pass  # already marked by callback

        return Response(result, status=200)

    except Exception as e:
        print(f"[VERIFY ERROR] {traceback.format_exc()}")
        return Response({"error": f"Server error: {str(e)}"}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])  # Safaricom calls this — no JWT
def mpesa_callback(request):
    """Safaricom STK Push callback — server-side payment confirmation."""
    try:
        body = request.data.get('Body', {})
        stk = body.get('stkCallback', {})
        result_code = stk.get('ResultCode')
        checkout_id = stk.get('CheckoutRequestID')

        if str(result_code) == '0' and checkout_id:
            try:
                order = Order.objects.get(checkout_request_id=checkout_id)
                order.is_paid = True
                order.status = 'Completed'
                order.save()
                order.items.all().update(purchased=True)
            except Order.DoesNotExist:
                pass

    except Exception:
        print(f"[CALLBACK ERROR] {traceback.format_exc()}")

    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

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
        print(f"[DOWNLOADS ERROR] {traceback.format_exc()}")
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
        print(f"[DOWNLOAD ERROR] {traceback.format_exc()}")
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
        print(f"[PAID IDS ERROR] {traceback.format_exc()}")
        return Response({"error": str(e)}, status=500)