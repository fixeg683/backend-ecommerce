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
# VIEWSETS (FIXED)
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
# PAYMENT (SAFE PLACEHOLDER)
# -------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    return Response({"message": "Payment initiation placeholder"})


@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    return Response({"message": "Callback received"})