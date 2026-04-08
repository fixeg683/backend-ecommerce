from .mpesa_utils import verify_mpesa_payment

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    checkout_request_id = request.data.get('checkout_request_id')
    if not checkout_request_id:
        return Response({"error": "checkout_request_id required"}, status=400)
    
    result = verify_mpesa_payment(checkout_request_id)
    return Response(result)