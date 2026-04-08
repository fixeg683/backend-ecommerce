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
        return Response({"error": str(e)}, status=500)