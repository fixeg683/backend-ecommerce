from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .models import Product, Order, OrderItem
from .serializers import ProductSerializer


# =========================
# AUTH
# =========================

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get("username")
    email = request.data.get("email")
    password = request.data.get("password")

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Username already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )

    refresh = RefreshToken.for_user(user)

    return Response({
        "message": "User created successfully",
        "refresh": str(refresh),
        "access": str(refresh.access_token),
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

    user = authenticate(
        username=user_obj.username,
        password=password
    )

    if user is not None:
        refresh = RefreshToken.for_user(user)

        return Response({
            "token": str(refresh.access_token),
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
    items = request.data.get("items", [])

    if not items:
        return Response(
            {"error": "No items provided"},
            status=status.HTTP_400_BAD_REQUEST
        )

    order = Order.objects.create(
        user=request.user,
        is_paid=False,
        payment_status="pending"
    )

    total_price = 0

    for item in items:
        try:
            product = Product.objects.get(id=item["product_id"])

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.get("quantity", 1)
            )

            total_price += float(product.price)

        except Product.DoesNotExist:
            continue

    order.total_price = total_price
    order.save()

    return Response({
        "success": True,
        "order_id": order.id,
        "total_price": total_price
    })


# =========================
# PAYMENT VERIFY
# =========================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    order_id = request.data.get("order_id")

    if not order_id:
        return Response(
            {"success": False, "message": "Order ID required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order = Order.objects.get(
            id=order_id,
            user=request.user
        )

        order.is_paid = True
        order.payment_status = "completed"
        order.save()

        return Response({
            "success": True,
            "message": "Payment completed successfully",
            "downloads_unlocked": True,
            "order_id": order.id
        })

    except Order.DoesNotExist:
        return Response({
            "success": False,
            "message": "Order not found"
        }, status=status.HTTP_404_NOT_FOUND)


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
                    "digital_file": item.product.digital_file.url if item.product.digital_file else "",
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
            "payment_status": order.payment_status,
            "total_price": order.total_price
        })

    return Response(data)