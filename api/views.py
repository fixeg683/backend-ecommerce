from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.contrib.auth.models import User
from .models import Product, Category, Order, OrderItem
from .serializers import (
    ProductSerializer,
    CategorySerializer,
    OrderSerializer,
    UserSerializer
)
from .mpesa_utils import initiate_mpesa_payment, format_phone, verify_mpesa_payment

# -------------------------
# ROOT
# -------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "message": "Welcome to the E-Space API",
        "status": "Running"
    })

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

# -------------------------
# AUTH
# -------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data.get('email'),
            password=request.data.get('password')
        )
        return Response({"message": "User created successfully"})
    return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

# -------------------------
# ORDERS
# -------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

# -------------------------
# DOWNLOADS
# -------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_downloads(request):
    items = OrderItem.objects.filter(order__user=request.user, purchased=True)
    products = [item.product for item in items]
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_product(request, product_id):
    try:
        item = OrderItem.objects.get(
            order__user=request.user,
            product_id=product_id,
            purchased=True
        )
        if item.product.file:
            return Response({"download_url": item.product.file.url})
        return Response({"error": "No file available"}, status=404)
    except OrderItem.DoesNotExist:
        return Response({"error": "Not authorized"}, status=403)

# -------------------------
# PAYMENT
# -------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    phone = request.data.get('phone')
    amount = request.data.get('amount')
    order_id = request.data.get('order_id')

    if not phone or not amount or not order_id:
        return Response({"error": "phone, amount, and order_id are required"}, status=400)

    phone = format_phone(phone)
    result = initiate_mpesa_payment(phone, amount, order_id)

    if 'error' in result:
        return Response({"error": result['error']}, status=500)

    return Response({
        "message": "STK push sent. Check your phone.",
        "CheckoutRequestID": result.get('CheckoutRequestID'),
        "ResponseDescription": result.get('ResponseDescription')
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    data = request.data
    try:
        body = data.get('Body', {}).get('stkCallback', {})
        result_code = body.get('ResultCode')
        checkout_request_id = body.get('CheckoutRequestID')

        if result_code == 0:
            metadata = body.get('CallbackMetadata', {}).get('Item', [])
            meta = {item['Name']: item.get('Value') for item in metadata}
            print(f"Payment confirmed: {meta.get('MpesaReceiptNumber')}, Phone: {meta.get('PhoneNumber')}, Amount: {meta.get('Amount')}")
        else:
            print(f"Payment failed. ResultCode: {result_code}")

    except Exception as e:
        print(f"Callback processing error: {e}")

    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    checkout_request_id = request.data.get('checkout_request_id')
    if not checkout_request_id:
        return Response({"error": "checkout_request_id required"}, status=400)
    result = verify_mpesa_payment(checkout_request_id)
    return Response(result)