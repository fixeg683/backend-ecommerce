from urllib import response

from rest_framework.decorators import action

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product').order_by('-id')

    @action(detail=False, methods=['get'], url_path='my-orders')
    def my_orders(self, request):
        """
        Return ONLY purchased products in a flat structure
        (perfect for frontend downloads page)
        """
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
                            "price": product.price,
                            "image": product.image.url if product.image else None,
                        }
                    })

        return response(data)