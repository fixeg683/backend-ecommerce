from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User

from .mpesa_utils import initiate_mpesa_payment, verify_mpesa_payment, get_access_token
from .models import Order, OrderItem, Product
from .serializers import OrderSerializer, ProductSerializer


# -----------------------------------
# HOME API
# -----------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def api_home(request):
    return Response({"message": "Backend API running successfully"})


# -----------------------------------
# REGISTER
# -----------------------------------

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username', '').strip()
    email    = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response(
            {"detail": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    if User.objects.filter(username=username).exists():
        return Response(
            {"detail": "A user with that username already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )
    if email and User.objects.filter(email=email).exists():
        return Response(
            {"detail": "A user with that email already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(username=username, email=email, password=password)
    return Response(
        {"detail": "Account created successfully.", "username": user.username},
        status=status.HTTP_201_CREATED
    )


# -----------------------------------
# PRODUCTS
# @authentication_classes([]) prevents an expired token from causing 401
# on a public endpoint before the permission check even runs.
# -----------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def product_list(request):
    products = Product.objects.select_related('category').all()
    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def product_detail(request, pk):
    try:
        product = Product.objects.select_related('category').get(pk=pk)
    except Product.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = ProductSerializer(product, context={'request': request})
    return Response(serializer.data)


# -----------------------------------
# INITIATE PAYMENT  (/api/pay/ and /api/payment/initiate/)
# Uses the mpesa_utils helper which handles sandbox vs production,
# phone formatting, retries, and friendly error messages.
# -----------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    phone       = request.data.get("phone", "").strip()
    amount      = request.data.get("amount", 1)
    product_ids = request.data.get("product_ids", [])

    if not phone:
        return Response(
            {"success": False, "error": "Phone number is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create the order in DB first so we have an order_id for the reference
    order = Order.objects.create(
        user=request.user,
        total_amount=amount,
        phone=phone,
        status='Pending',
        is_paid=False,
    )
    for pid in product_ids:
        try:
            product = Product.objects.get(pk=pid)
            OrderItem.objects.create(order=order, product=product)
        except Product.DoesNotExist:
            pass

    # Fire STK Push via the utility (handles auth, formatting, retries)
    result = initiate_mpesa_payment(phone=phone, amount=amount, order_id=order.id)

    if "error" in result:
        # Clean up the pending order so we don't leave orphans
        order.delete()
        return Response(
            {"success": False, "error": result["error"]},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Store the CheckoutRequestID so the callback can find the order
    checkout_id = result.get("CheckoutRequestID")
    order.checkout_request_id = checkout_id
    order.save(update_fields=["checkout_request_id"])

    return Response({
        "success": True,
        "CheckoutRequestID": checkout_id,
        "checkout_id": checkout_id,
        "message": "STK Push sent successfully. Enter your M-Pesa PIN."
    })


# -----------------------------------
# VERIFY PAYMENT  (/api/verify-payment/ and /api/payment/verify/)
# First checks our DB (fastest path), then queries Safaricom if needed.
# -----------------------------------

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_payment(request):
    checkout_id = (
        request.data.get("checkout_request_id") or
        request.data.get("checkout_id", "")
    ).strip()

    if not checkout_id:
        return Response(
            {"success": False, "message": "Checkout ID is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1 — check our own DB first (populated by the M-Pesa callback)
    try:
        order = Order.objects.get(checkout_request_id=checkout_id)
        if order.is_paid:
            return Response({"success": True, "confirmed": True,
                             "message": "Payment confirmed."})
    except Order.DoesNotExist:
        return Response({"success": False, "confirmed": False,
                         "message": "Order not found."})

    # 2 — DB not yet updated; ask Safaricom directly
    result = verify_mpesa_payment(checkout_id)

    if result.get("ResultCode") == "pending":
        return Response({"success": False, "confirmed": False,
                         "message": "Payment still processing."})

    if str(result.get("ResultCode", "")) == "0":
        order.is_paid = True
        order.status = 'Completed'
        order.save()
        order.items.update(purchased=True)
        return Response({"success": True, "confirmed": True,
                         "message": "Payment confirmed."})

    # Non-zero ResultCode = user cancelled / wrong PIN / etc.
    return Response({"success": False, "confirmed": False,
                     "message": result.get("ResultDesc", "Payment not confirmed.")})


# -----------------------------------
# M-PESA CALLBACK  (/api/payment/callback/)
# Called by Safaricom servers — marks orders paid in DB.
# -----------------------------------

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_callback(request):
    try:
        body        = request.data.get('Body', {})
        stk         = body.get('stkCallback', {})
        result_code = stk.get('ResultCode')
        checkout_id = stk.get('CheckoutRequestID')

        print(f"[CALLBACK] checkout_id={checkout_id} result_code={result_code}")

        if checkout_id and result_code == 0:
            try:
                order = Order.objects.get(checkout_request_id=checkout_id)
                order.is_paid = True
                order.status  = 'Completed'
                order.save()
                order.items.update(purchased=True)
                print(f"[CALLBACK] Order {order.id} marked as paid.")
            except Order.DoesNotExist:
                print(f"[CALLBACK] No order found for checkout_id={checkout_id}")

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        print(f"[CALLBACK] Exception: {e}")
        return Response({"ResultCode": 1, "ResultDesc": str(e)})


# -----------------------------------
# CHECK DOWNLOAD ACCESS
# -----------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def check_download_access(request):
    unlocked = request.query_params.get("unlocked")
    if unlocked == "true":
        return Response({"success": True,  "downloads_unlocked": True})
    return Response({"success": False, "downloads_unlocked": False})


# -----------------------------------
# DOWNLOAD FILE
# -----------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def download_file(request):
    if request.query_params.get("unlocked") != "true":
        return Response({"success": False, "message": "Payment required"},
                        status=status.HTTP_403_FORBIDDEN)
    return Response({"success": True, "file_url": "https://example.com/file.zip"})


# -----------------------------------
# M-PESA HEALTH CHECK
# -----------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_health(request):
    token, err = get_access_token()
    if token:
        return Response({"status": "healthy",
                         "message": "M-Pesa credentials are valid and working."})
    return Response({"status": "unhealthy", "message": err},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------------------
# MY ORDERS
# -----------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    try:
        orders     = Order.objects.filter(user=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"success": False, "message": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)