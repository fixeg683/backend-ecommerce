import json
import logging
from typing import AsyncGenerator, Optional
import asyncio

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from django.conf import settings
from .recommendation_service import get_recommended_products
from .memory_service import get_chat_history
from api.models import Order

logger = logging.getLogger(__name__)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": "Get product recommendations based on user's browse and purchase history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recommendations to return"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "track_order",
            "description": "Check the status of an order given an order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The ID or checkout request ID of the order"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get details of a specific product",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "The ID of the product"
                    }
                },
                "required": ["product_id"]
            }
        }
    }
]

async def get_chat_stream(session_id: int, user_id: Optional[int], message: str) -> AsyncGenerator[str, None]:
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not AsyncOpenAI or not api_key:
        yield json.dumps({"type": "message", "content": _fallback_reply(message)})
        return

    client = AsyncOpenAI(api_key=api_key)
    
    # Get previous history
    messages = await get_chat_history(session_id)
    
    # Add new user message to the context
    messages.append({"role": "user", "content": message})

    try:
        response = await client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are a helpful commerce assistant for an e-commerce store. Be concise and polite. Use tools if necessary to fetch product recommendations or track orders."}
            ] + messages,
            tools=tools,
            stream=True
        )

        tool_calls = []
        
        async for chunk in response:
            delta = chunk.choices[0].delta
            
            if delta.content:
                yield json.dumps({"type": "content", "content": delta.content})
                
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if len(tool_calls) <= tool_call.index:
                        tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    
                    if tool_call.id:
                        tool_calls[tool_call.index]["id"] = tool_call.id
                    if tool_call.function.name:
                        tool_calls[tool_call.index]["function"]["name"] = tool_call.function.name
                    if tool_call.function.arguments:
                        tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments

        if tool_calls:
            # We have tool calls to execute!
            messages.append({"role": "assistant", "tool_calls": tool_calls})
            
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                    
                result = await execute_tool(func_name, args, user_id, session_id)
                
                # If the tool is get_recommendations, we might also want to send a custom message type
                # to the frontend to render product cards. We can yield a custom JSON event for that.
                if func_name == "get_recommendations" and result:
                    # result is list of dicts
                    yield json.dumps({"type": "products", "products": result})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": func_name,
                        "content": "Rendered product cards to user. Summarize briefly."
                    })
                else:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": func_name,
                        "content": json.dumps(result)
                    })

            # Second pass
            response2 = await client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": "You are a helpful commerce assistant for an e-commerce store. Be concise and polite. Use tools if necessary to fetch product recommendations or track orders."}
                ] + messages,
                stream=True
            )
            
            async for chunk in response2:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield json.dumps({"type": "content", "content": delta.content})
                    
    except Exception as e:
        logger.error(f"OpenAI API Error: {e}")
        yield json.dumps({"type": "message", "content": _fallback_reply(message)})

async def execute_tool(name: str, args: dict, user_id: Optional[int], session_id: int):
    if name == "get_recommendations":
        from .recommendation_service import get_recommended_products_async
        limit = args.get("limit", 3)
        return await get_recommended_products_async(user_id=user_id, session_id=session_id, limit=limit)
    elif name == "track_order":
        from .order_service import track_order_async
        order_id = args.get("order_id")
        return await track_order_async(order_id, user_id)
    elif name == "get_product_details":
        from .recommendation_service import get_product_details_async
        product_id = args.get("product_id")
        return await get_product_details_async(product_id)
    return {"error": "Unknown function"}

def _fallback_reply(message: str) -> str:
    text = (message or '').strip().lower()
    if 'recommend' in text or 'product' in text:
        return 'I can recommend top products based on your style and budget. Tell me what you are shopping for.'
    if 'order' in text or 'delivery' in text:
        return 'I can help you check the status of your order. Share your order number or email address.'
    if 'hello' in text or 'hi' in text:
        return 'Hello! I can help you browse products, track orders, or answer questions about downloads.'
    return 'Thanks for reaching out. I can help you browse products, make purchases, or track orders.'
