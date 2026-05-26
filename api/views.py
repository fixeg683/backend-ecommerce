from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .models import Product, Order, OrderItem
from .serializers import ProductSerializer, RegisterSerializer
from .mpesa_utils import initiate_mpesa_payment, verify_mpesa_payment


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

    user = authenticate(
        username=user_obj.username,
        password=password
    )

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
        serializer = ProductSerializer(product)

        return Response(serializer.data)

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

    # Create order record
    order = Order.objects.create(
        user=request.user,
        total_amount=amount,
        phone=phone_number,
        status='Pending'
    )

    # Attach items if provided
    for pid in product_ids:
        try:
            product = Product.objects.get(id=pid)
            OrderItem.objects.create(order=order, product=product)
        except Product.DoesNotExist:
            continue

    # Initiate M-Pesa STK Push
    result = initiate_mpesa_payment(phone_number, amount, order.id)

    if isinstance(result, dict) and result.get('error'):
        order.delete()
        return Response({"error": result.get('error')}, status=status.HTTP_400_BAD_REQUEST)

    # Save Safaricom CheckoutRequestID if present
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
    checkout_request_id = request.data.get("checkout_request_id") or request.data.get("CheckoutRequestID")

    if not checkout_request_id:
        return Response({"success": False, "message": "checkout_request_id required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        order = Order.objects.get(
            checkout_request_id=checkout_request_id,
            user=request.user
        )
    except Order.DoesNotExist:
        return Response({"success": False, "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    result = verify_mpesa_payment(checkout_request_id)

    if isinstance(result, dict) and result.get('error'):
        return Response({"success": False, "message": result.get('error')}, status=status.HTTP_400_BAD_REQUEST)

    if result.get('ResultCode') == 'pending' or str(result.get('ResultCode')) == 'pending':
        return Response({"success": False, "confirmed": False, "message": "Payment still processing"})

    if str(result.get('ResultCode')) == '0' or str(result.get('ResultCode')) == '0.0':
        order.is_paid = True
        order.status = 'Completed'
        order.save()
        return Response({"success": True, "confirmed": True, "order_id": order.id})

    return Response({
        "success": False,
        "confirmed": False,
        "message": result.get('ResultDesc', 'Payment not confirmed')
    })


# =========================
# MPESA CALLBACK
# =========================
import json
import logging
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    try:
        data = request.data
        if not data:
            data = json.loads(request.body)
            
        logger.info(f"M-Pesa Callback Data: {data}")
        
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        
        if not checkout_request_id:
            return Response({"ResultCode": 0, "ResultDesc": "Accepted, but missing checkout ID"})

        try:
            order = Order.objects.get(checkout_request_id=checkout_request_id)
        except Order.DoesNotExist:
            return Response({"ResultCode": 0, "ResultDesc": "Accepted, order not found"})

        if str(result_code) == '0' or str(result_code) == '0.0':
            order.is_paid = True
            order.status = 'Completed'
        else:
            order.status = 'Failed'
            
        order.save()

        # Always return Success to Safaricom so they stop retrying
        return Response({
            "ResultCode": 0,
            "ResultDesc": "Accepted"
        })

    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        # Still return 200 so Safaricom doesn't retry on our internal errors
        return Response({
            "ResultCode": 0,
            "ResultDesc": "Accepted but errored internally"
        })


# =========================
# USER DOWNLOADS
# =========================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_downloads(request):

    paid_orders = Order.objects.filter(
        user=request.user,
        is_paid=True
    )

    products = []

    for order in paid_orders:
        order_items = OrderItem.objects.filter(order=order)

        for item in order_items:
            if item.product:
                products.append({
                    "id": item.product.id,
                    "name": item.product.name,
                    "price": item.product.price,
                    "image": item.product.image.url if item.product.image else "",
                    "downloadable_file": item.product.downloadable_file if item.product.downloadable_file else "",
                })

    return Response({
        "paid": True,
        "products": products
    })


# =========================
# USER ORDERS
# =========================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_orders(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by('-id')

    data = []

    for order in orders:
        data.append({
            "id": order.id,
            "is_paid": order.is_paid,
            "status": order.status,
            "total_amount": order.total_amount
        })

    return Response(data)