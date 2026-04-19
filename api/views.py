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

        if item.product.file:
            return Response({"download_url": item.product.file.url})

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
