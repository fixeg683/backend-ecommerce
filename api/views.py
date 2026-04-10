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

# -------------------------
# PAYMENT
# -------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    try:
        phone = request.data.get('phone')
        amount = request.data.get('amount')
        product_ids = request.data.get('product_ids', [])

        print(f"[PAY] Request - phone: {phone}, amount: {amount}, products: {product_ids}")

        if not phone or not amount:
            return Response({"error": "phone and amount are required"}, status=400)

        if not product_ids:
            return Response({"error": "product_ids are required"}, status=400)

        phone = format_phone(phone)
        print(f"[PAY] Formatted phone: {phone}")

        # Create order
        try:
            order = Order.objects.create(
                user=request.user,
                total_amount=amount,
                phone=phone,
                status='Pending',
                is_paid=False
            )
            print(f"[PAY] Order created: {order.id}")
        except Exception as e:
            print(f"[PAY] Order creation failed: {traceback.format_exc()}")
            return Response({"error": f"Could not create order: {str(e)}"}, status=500)

        # Create order items
        try:
            products = Product.objects.filter(id__in=product_ids)
            print(f"[PAY] Products found: {list(products.values_list('id', flat=True))}")
            for product in products:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    purchased=False
                )
        except Exception as e:
            print(f"[PAY] OrderItem creation failed: {traceback.format_exc()}")
            return Response({"error": f"Could not create order items: {str(e)}"}, status=500)

        # Initiate STK push
        print(f"[PAY] Initiating STK push...")
        result = initiate_mpesa_payment(phone, amount, order.id)
        print(f"[PAY] M-Pesa result: {result}")

        if 'error' in result:
            order.status = 'Failed'
            order.save()
            return Response({"error": result['error']}, status=500)

        # Check for M-Pesa error response code
        if result.get('ResponseCode') != '0':
            order.status = 'Failed'
            order.save()
            print(f"[PAY] STK push rejected: {result}")
            return Response({
                "error": result.get('ResponseDescription', 'STK push failed'),
                "detail": result
            }, status=500)

        checkout_id = result.get('CheckoutRequestID')
        order.checkout_request_id = checkout_id
        order.save()
        print(f"[PAY] STK push success. CheckoutRequestID: {checkout_id}")

        return Response({
            "message": "STK push sent. Check your phone.",
            "CheckoutRequestID": checkout_id,
            "ResponseDescription": result.get('ResponseDescription')
        })

    except Exception as e:
        print(f"[PAY] Unexpected error: {traceback.format_exc()}")
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    data = request.data
    try:
        body = data.get('Body', {}).get('stkCallback', {})
        result_code = body.get('ResultCode')
        checkout_request_id = body.get('CheckoutRequestID')
        print(f"[CALLBACK] ResultCode: {result_code}, CheckoutID: {checkout_request_id}")

        if result_code == 0:
            metadata = body.get('CallbackMetadata', {}).get('Item', [])
            meta = {item['Name']: item.get('Value') for item in metadata}
            print(f"[CALLBACK] Payment confirmed: receipt={meta.get('MpesaReceiptNumber')}, "
                  f"phone={meta.get('PhoneNumber')}, amount={meta.get('Amount')}")
            try:
                order = Order.objects.get(checkout_request_id=checkout_request_id)
                order.is_paid = True
                order.status = 'Completed'
                order.save()
                order.items.update(purchased=True)
                print(f"[CALLBACK] Order {order.id} marked as paid")
            except Order.DoesNotExist:
                print(f"[CALLBACK] Order not found for: {checkout_request_id}")
        else:
            print(f"[CALLBACK] Payment failed. ResultCode: {result_code}")
            try:
                order = Order.objects.get(checkout_request_id=checkout_request_id)
                order.status = 'Failed'
                order.save()
            except Order.DoesNotExist:
                pass

    except Exception as e:
        print(f"[CALLBACK] Error: {traceback.format_exc()}")

    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    try:
        checkout_request_id = request.data.get('checkout_request_id')
        if not checkout_request_id:
            return Response({"error": "checkout_request_id required"}, status=400)
        print(f"[VERIFY] Checking: {checkout_request_id}")
        result = verify_mpesa_payment(checkout_request_id)
        print(f"[VERIFY] Result: {result}")
        return Response(result)
    except Exception as e:
        print(f"[VERIFY] Error: {traceback.format_exc()}")
        return Response({"error": str(e)}, status=500)