from asgiref.sync import sync_to_async
from api.models import Product, Order
from chatbot.models import BrowseHistory
from typing import Optional
import json

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
from django.conf import settings

@sync_to_async
def _get_user_context(user_id: Optional[int], session_id: int):
    # Fetch recent purchases
    purchased_products = []
    if user_id:
        orders = Order.objects.filter(user_id=user_id, status='Completed').prefetch_related('items__product').order_by('-created_at')[:5]
        for order in orders:
            for item in order.items.all():
                purchased_products.append(item.product.name)

    # Fetch recent browse history
    browse_qs = BrowseHistory.objects.all()
    if user_id:
        browse_qs = browse_qs.filter(user_id=user_id)
    elif session_id:
        browse_qs = browse_qs.filter(session_id=session_id)
        
    recent_browse = browse_qs.select_related('product').order_by('-viewed_at')[:10]
    browsed_products = [b.product.name for b in recent_browse]

    return {
        "purchased": list(set(purchased_products)),
        "browsed": list(set(browsed_products))
    }

@sync_to_async
def _get_all_active_products():
    products = Product.objects.all().order_by('-created_at')[:50]
    return [
        {
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'description': p.description,
            'category': p.category.name if p.category else 'Unknown',
            'image': p.image.url if p.image else None,
        }
        for p in products
    ]

@sync_to_async
def get_product_details_async(product_id: int):
    p = Product.objects.filter(id=product_id).first()
    if not p:
        return {"error": "Product not found"}
    return {
        'id': p.id,
        'name': p.name,
        'price': float(p.price),
        'description': p.description,
        'category': p.category.name if p.category else 'Unknown',
        'stock': p.stock
    }

async def get_recommended_products_async(user_id: Optional[int], session_id: int, limit: int = 3):
    context = await _get_user_context(user_id, session_id)
    all_products = await _get_all_active_products()
    
    if not all_products:
        return []

    # Cold start fallback if no context or no OpenAI
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not context["purchased"] and not context["browsed"] or not AsyncOpenAI or not api_key:
        # Just return the latest
        return all_products[:limit]

    # Ask GPT to rank products based on context
    try:
        client = AsyncOpenAI(api_key=api_key)
        
        prompt = f"""
        User Context:
        Purchased: {', '.join(context['purchased']) or 'None'}
        Recently Viewed: {', '.join(context['browsed']) or 'None'}
        
        Available Products (JSON):
        {json.dumps([{'id': p['id'], 'name': p['name'], 'category': p['category']} for p in all_products])}
        
        Rank the top {limit} products most relevant to the user's interests. 
        Return ONLY a JSON array of the recommended product IDs (integers).
        """
        
        response = await client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"} # We might need to adjust prompt to return dict if using json_object, but let's just ask for json string of list
        )
        # Note: gpt-4o-mini response_format=json_object requires outputting a JSON object.
        # So we update prompt:
        prompt += "\nReturn a JSON object with a single key 'product_ids' containing the array of integer IDs."
        
        response = await client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result_str = response.choices[0].message.content
        data = json.loads(result_str)
        recommended_ids = data.get("product_ids", [])
        
        # Filter all_products
        recommended = [p for p in all_products if p['id'] in recommended_ids]
        
        # Fill with remaining if not enough
        if len(recommended) < limit:
            remaining = [p for p in all_products if p not in recommended]
            recommended.extend(remaining[:limit - len(recommended)])
            
        return recommended[:limit]
        
    except Exception as e:
        print(f"Error in recommendation_service: {e}")
        return all_products[:limit]

# Sync versions for backwards compatibility or REST endpoints if needed
from asgiref.sync import async_to_sync

def get_recommended_products(user=None, session=None, limit=3):
    user_id = user.id if user and user.is_authenticated else None
    session_id = session.id if session else None
    return async_to_sync(get_recommended_products_async)(user_id, session_id, limit)
