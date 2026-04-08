# ✅ ALL imports at the very top — nothing before these
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

# rest of your views below...