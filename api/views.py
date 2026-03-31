from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Product, Order
from .serializers import ProductSerializer, OrderSerializer
from .mpesa_utils import send_stk_push

# --- 1. Product Management ---
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Handles listing products and retrieving a single product.
    Note: Creation/Updates are done via Django Admin as per requirements.
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
    """
    Expects: { "phone": "2547XXXXXXXX", "amount": 100 }
    """
    user = request.user
    phone = request.data.get('phone')
    amount = request.data.get('amount')

    if not phone or not amount:
        return Response({"detail": "Phone and amount are required"}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Create a Pending Order in our DB
    order = Order.objects.create(
        user=user, 
        total_amount=amount, 
        phone=phone,
        status='Pending'
    )

    # 2. Trigger Safaricom API
    try:
        mpesa_response = send_stk_push(phone, amount, order.id)
        
        if mpesa_response.get('ResponseCode') == '0':
            # Save the CheckoutRequestID to match the callback later
            order.checkout_request_id = mpesa_response.get('CheckoutRequestID')
            order.save()
            return Response({
                "message": "STK Push sent successfully",
                "checkout_id": order.checkout_request_id
            }, status=status.HTTP_200_OK)
        else:
            order.status = 'Failed'
            order.save()
            return Response({"detail": "M-Pesa Gateway Error"}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({"detail": f"Internal Server Error: {str(e)}"}, status=500)

# --- 4. Payment: M-Pesa Callback ---
@api_view(['POST'])
@permission_classes([AllowAny]) # Safaricom doesn't send JWTs
def mpesa_callback(request):
    """
    This endpoint is hit by Safaricom's servers asynchronously.
    """
    data = request.data.get('Body', {}).get('stkCallback', {})
    result_code = data.get('ResultCode')
    checkout_request_id = data.get('CheckoutRequestID')

    try:
        order = Order.objects.get(checkout_request_id=checkout_request_id)
        
        if result_code == 0:
            # Payment Successful
            order.status = 'Completed'
            order.is_paid = True
            # Extract receipt number if needed
            items = data.get('CallbackMetadata', {}).get('Item', [])
            for item in items:
                if item.get('Name') == 'MpesaReceiptNumber':
                    order.transaction_id = item.get('Value')
        else:
            # Payment Cancelled or Failed
            order.status = 'Failed'
        
        order.save()
    except Order.DoesNotExist:
        # Log this error; might be a delayed callback or fake request
        pass

    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

# --- 5. Order History ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)