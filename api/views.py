from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Product, Order
from .serializers import ProductSerializer, OrderSerializer
# from .mpesa_utils import send_stk_push  # Uncomment once this file exists

# --- 0. API Welcome Root ---
@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    Shows a welcome message at the base URL so users don't see a 404.
    """
    return Response({
        "status": "Online",
        "message": "Welcome to the Backend E-commerce API",
        "endpoints": {
            "admin": "/admin/",
            "products": "/api/products/",
            "auth_token": "/api/token/"
        }
    })

# --- 1. Product Management ---
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Handles listing products and retrieving a single product.
    """
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

# --- 2. Authentication: Signup ---
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    data = request.data
    try:
        if User.objects.filter(username=data.get('username')).exists():
            return Response({"detail": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password')
        )
        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# --- 3. Payment: Initiate M-Pesa STK Push ---
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    user = request.user
    phone = request.data.get('phone')
    amount = request.data.get('amount')

    if not phone or not amount:
        return Response({"detail": "Phone and amount are required"}, status=status.HTTP_400_BAD_REQUEST)

    order = Order.objects.create(
        user=user, 
        total_amount=amount, 
        phone=phone,
        status='Pending'
    )

    # Note: Ensure mpesa_utils.py is configured before using send_stk_push
    try:
        # mpesa_response = send_stk_push(phone, amount, order.id)
        # Placeholder logic for testing without the M-Pesa API key
        return Response({
            "message": "Order created. Connect M-Pesa API to trigger STK Push.",
            "order_id": order.id
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"detail": f"Internal Error: {str(e)}"}, status=500)

# --- 4. Payment: M-Pesa Callback ---
@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    data = request.data.get('Body', {}).get('stkCallback', {})
    result_code = data.get('ResultCode')
    checkout_request_id = data.get('CheckoutRequestID')

    try:
        order = Order.objects.get(checkout_request_id=checkout_request_id)
        if result_code == 0:
            order.status = 'Completed'
            order.is_paid = True
            items = data.get('CallbackMetadata', {}).get('Item', [])
            for item in items:
                if item.get('Name') == 'MpesaReceiptNumber':
                    order.transaction_id = item.get('Value')
        else:
            order.status = 'Failed'
        order.save()
    except Order.DoesNotExist:
        pass

    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

# --- 5. Order History ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)