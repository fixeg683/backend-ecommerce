from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.conf import settings

from .models import Product, Order, OrderItem, Category
from .serializers import ProductSerializer
from .mpesa_utils import initiate_mpesa_payment, verify_mpesa_payment


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
def api_root(request):
    """
    Root API endpoint (prevents 404 and import error)
    """
    return Response({
        "message": "Welcome to E-Commerce API",
        "endpoints": {
            "products": "/api/products/",
            "login": "/api/token/",
            "register": "/api/register/",
            "cart": "/api/orders/",
            "downloads": "/api/my-downloads/"
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user
    """
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    if not all([username, email, password]):
        return Response(
            {"error": "username, email, and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Username already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(username=username, email=email, password=password)
    token, created = Token.objects.get_or_create(user=user)

    return Response(
        {"token": token.key, "user_id": user.id},
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get current user info
    """
    return Response({
        "id": request.user.id,
        "username": request.user.username,
        "email": request.user.email
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    """
    Initiate M-Pesa payment for order
    """
    phone = request.data.get('phone')
    amount = request.data.get('amount')
    order_id = request.data.get('order_id')

    if not all([phone, amount, order_id]):
        return Response(
            {"error": "phone, amount, and order_id are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    response = initiate_mpesa_payment(phone, amount)
    
    if response.get('ResponseCode') == '0':
        order.checkout_request_id = response.get('CheckoutRequestID')
        order.phone = phone
        order.save()
        return Response(response, status=status.HTTP_200_OK)
    else:
        return Response(response, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    """
    M-Pesa callback endpoint
    """
    data = request.data.get('Body', {})
    result = data.get('stkCallback', {})
    request_id = result.get('CheckoutRequestID')
    result_code = result.get('ResultCode')

    try:
        order = Order.objects.get(checkout_request_id=request_id)
        if result_code == 0:
            order.is_paid = True
            order.status = 'Completed'
            # Mark all items as purchased
            order.items.all().update(purchased=True)
        else:
            order.status = 'Failed'
        order.save()
    except Order.DoesNotExist:
        pass

    return Response({"ResultCode": 0})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    """
    Get user's orders
    """
    orders = Order.objects.filter(user=request.user)
    data = []
    for order in orders:
        items = order.items.all()
        data.append({
            "id": order.id,
            "total_amount": str(order.total_amount),
            "status": order.status,
            "is_paid": order.is_paid,
            "created_at": order.created_at,
            "items": [
                {
                    "product_id": item.product.id,
                    "product_name": item.product.name,
                    "price": str(item.product.price),
                    "purchased": item.purchased
                }
                for item in items
            ]
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_downloads(request):
    """
    Return purchased products with download links
    """
    items = OrderItem.objects.filter(
        order__user=request.user,
        purchased=True
    )

    data = [
        {
            "id": item.product.id,
            "name": item.product.name,
            "download_url": f"/api/download/{item.product.id}/"
        }
        for item in items
    ]

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_product(request, product_id):
    """
    Secure download (ONLY if purchased)
    """
    item = get_object_or_404(
        OrderItem,
        order__user=request.user,
        product_id=product_id,
        purchased=True
    )

    return FileResponse(item.product.file.open(), as_attachment=True)