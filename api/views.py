from rest_framework import viewsets, permissions
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # Explicitly AllowAny to prevent 401s on the Product List
    permission_classes = [permissions.AllowAny] 

# Ensure this view exists for your downloads
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_downloads(request):
    # your existing logic to return paid products
    pass