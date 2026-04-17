from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import FileResponse
from .models import Order
from products.models import Product

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    payment_id = request.data.get('payment_id')
    order_id = request.data.get('order_id')

    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    # 👉 TODO: Add real payment verification (PayPal / M-Pesa API)

    order.is_paid = True
    order.payment_id = payment_id
    order.save()

    return Response({"message": "Payment successful"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_access(request, product_id):
    is_paid = Order.objects.filter(
        user=request.user,
        product_id=product_id,
        is_paid=True
    ).exists()

    return Response({"is_paid": is_paid})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_product(request, product_id):
    order = Order.objects.filter(
        user=request.user,
        product_id=product_id,
        is_paid=True
    ).first()

    if not order:
        return Response({"error": "You must purchase this product"}, status=403)

    product = Product.objects.get(id=product_id)

    return FileResponse(product.file.open(), as_attachment=True)