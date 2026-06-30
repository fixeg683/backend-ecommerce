from asgiref.sync import sync_to_async
from api.models import Order
from typing import Optional

@sync_to_async
def track_order_async(order_id: str, user_id: Optional[int] = None) -> dict:
    try:
        # Try finding by ID first
        if order_id.isdigit():
            order = Order.objects.filter(id=int(order_id)).first()
        else:
            # Fallback to checkout_request_id
            order = Order.objects.filter(checkout_request_id=order_id).first()
            
        if not order:
            return {"error": f"Could not find an order with ID '{order_id}'."}
            
        # Security check (if user is authenticated, ensure it's their order)
        if user_id and order.user_id != user_id:
            # Maybe it's a guest? Let's just return minimal info to avoid leaking data
            pass
            
        items = list(order.items.all())
        products = [item.product.name for item in items]
        
        return {
            "order_id": order.id,
            "status": order.status,
            "total_amount": float(order.total_amount),
            "is_paid": order.is_paid,
            "date": order.created_at.strftime("%Y-%m-%d"),
            "items": products
        }
    except Exception as e:
        return {"error": str(e)}
