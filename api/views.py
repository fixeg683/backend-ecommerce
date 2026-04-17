from rest_framework.decorators import api_view, permission_classes, action
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
        """
        Returns purchased products in flat structure for frontend
        """
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
                            "price": product.price,
                            "image": product.image.url if product.image else None,
                        }
                    })

        return Response(data)

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

# DOWNLOADS

# -------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_downloads(request):
    try:
        items = OrderItem.objects.filter(
            order__user=request.user,
            purchased=True
        ).select_related('product')

        products = [item.product for item in items]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    except Exception as e:
        print(f"Downloads error: {traceback.format_exc()}")
        return Response({"error": str(e)}, status=500)

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
