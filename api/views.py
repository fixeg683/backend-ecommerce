from django.contrib.auth.models import User
from django.http import FileResponse, Http404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import os

from .models import Product, Order, PaidProduct
from .serializers import ProductSerializer, OrderSerializer

# --- 0. API Root ---
@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "status": "Online",
        "message": "Welcome to the E-Space API",
    })

# --- 1. Products ---
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

# --- 2. Register ---
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    data = request.data
    name = data.get('name') or data.get('username', '')
    email = data.get('email', '')
    password = data.get('password', '')

    if not name or not email or not password:
        return Response(
            {"detail": "Name, email and password are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    if User.objects.filter(username=email).exists():
        return Response(
            {"detail": "An account with this email already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        User.objects.create_user(
            username=email, email=email, password=password,
            first_name=name.split()[0],
            last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
        )
        return Response({"message": "Account created."}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# --- 3. Current User ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    user = request.user
    return Response({
        "id": user.id,
        "name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "email": user.email,
        "username": user.username,
    })

# --- 4. Payment ---
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    user = request.user
    phone = request.data.get('phone')
    amount = request.data.get('amount')
    product_ids = request.data.get('product_ids', [])  # ← list of product IDs

    if not phone or not amount:
        return Response(
            {"detail": "Phone and amount are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    order = Order.objects.create(
        user=user,
        total_amount=amount,
        phone=phone,
        status='Completed',  # Simulate success for now
        is_paid=True
    )

    # ✅ Record each product as paid for this user
    for product_id in product_ids:
        try:
            product = Product.objects.get(id=product_id)
            PaidProduct.objects.get_or_create(
                user=user,
                product=product,
                defaults={'order': order}
            )
        except Product.DoesNotExist:
            pass

    return Response({
        "message": "Payment recorded. You can now download your products.",
        "order_id": order.id
    }, status=status.HTTP_200_OK)

# --- 5. Check which products the user has paid for ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_paid_products(request):
    paid = PaidProduct.objects.filter(user=request.user).values_list('product_id', flat=True)
    return Response(list(paid))

# --- 6. Secure download — only if paid ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_product(request, product_id):
    user = request.user
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise Http404("Product not found.")

    # Check payment
    if not PaidProduct.objects.filter(user=user, product=product).exists():
        return Response(
            {"detail": "Purchase required. Please complete payment to download."},
            status=status.HTTP_403_FORBIDDEN
        )

    if not product.file:
        return Response(
            {"detail": "No downloadable file for this product."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Serve the file
    try:
        file_url = product.file.url  # Cloudinary URL
        return Response({"download_url": file_url})
    except Exception as e:
        return Response({"detail": str(e)}, status=500)

# --- 7. M-Pesa Callback ---
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

# --- 8. Order History ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)