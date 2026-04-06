from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import FileResponse

from .models import OrderItem


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