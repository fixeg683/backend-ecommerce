# api/views.py

from rest_framework.decorators import api_view, permission_classes # ADD THIS LINE
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status, viewsets
# ... your other imports (models, serializers, etc.)

@api_view(['GET'])
def api_root(request):
    return Response({
        "message": "Welcome to the E-Space API",
        "status": "Running"
    })

# Ensure your other views also have the correct decorators
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_downloads(request):
    # your logic here
    return Response({"message": "Success"})