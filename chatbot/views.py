from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.models import OrderItem, Product
from .models import ChatMessage, ChatSession, Lead, RecommendationLog, UserPreference


@api_view(['POST'])
@permission_classes([AllowAny])
def create_session(request):
    session = ChatSession.objects.create(title='New chat')
    return Response({'id': session.id, 'title': session.title})


@api_view(['GET'])
@permission_classes([AllowAny])
def session_history(request, session_id):
    session = ChatSession.objects.filter(id=session_id).first()
    if not session:
        return Response({'error': 'Session not found'}, status=404)
    messages = session.messages.all().values('id', 'role', 'content', 'created_at', 'metadata')
    return Response({'id': session.id, 'messages': list(messages)})


@api_view(['POST'])
@permission_classes([AllowAny])
def send_message(request, session_id):
    from asgiref.sync import async_to_sync
    
    session = ChatSession.objects.filter(id=session_id).first()
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    message_text = (request.data.get('message') or '').strip()
    if not message_text:
        return Response({'error': 'Message is required'}, status=400)

    # Note: send_message via REST is now mostly a fallback if websockets fail.
    # It doesn't support streaming. We just gather all content.
    
    ChatMessage.objects.create(session=session, role='user', content=message_text)

    try:
        from .services.openai_service import get_chat_stream
        
        user_id = request.user.id if request.user.is_authenticated else None
        
        async def run_stream():
            full_content = ""
            async for chunk in get_chat_stream(session.id, user_id, message_text):
                import json
                chunk_data = json.loads(chunk)
                if chunk_data.get("type") == "content":
                    full_content += chunk_data.get("content", "")
                elif chunk_data.get("type") == "message":
                    full_content = chunk_data.get("content", "")
            return full_content
            
        reply_text = async_to_sync(run_stream)()
        
        assistant_message = ChatMessage.objects.create(session=session, role='assistant', content=reply_text)
        
        session.title = message_text[:40] or session.title
        session.save(update_fields=['title', 'updated_at'])
        
        return Response({'message': {'id': assistant_message.id, 'role': 'assistant', 'content': reply_text}})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def capture_lead(request):
    data = request.data
    lead = Lead.objects.create(
        name=data.get('name', ''),
        email=data.get('email', ''),
        phone=data.get('phone', ''),
        message=data.get('message', ''),
        source=data.get('source', 'chat'),
    )
    return Response({'id': lead.id, 'message': 'Lead captured'})


@api_view(['POST'])
@permission_classes([AllowAny])
def track_view(request):
    product_id = request.data.get('product_id')
    session_id = request.data.get('session_id')
    if not product_id:
        return Response({'error': 'product_id is required'}, status=400)
        
    user = request.user if request.user.is_authenticated else None
    
    # Track in BrowseHistory
    try:
        from .models import BrowseHistory
        from api.models import Product
        from .models import ChatSession
        
        product = Product.objects.filter(id=product_id).first()
        if product:
            session = None
            if session_id:
                session = ChatSession.objects.filter(id=session_id).first()
                
            BrowseHistory.objects.create(
                user=user,
                session=session,
                product=product
            )
            return JsonResponse({'status': 'view tracked', 'product_id': product_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
        
    return JsonResponse({'status': 'product not found'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def track_click(request):
    product_id = request.data.get('product_id')
    session_id = request.data.get('session_id')
    if not product_id:
        return Response({'error': 'product_id is required'}, status=400)
        
    try:
        from .models import RecommendationLog, ChatSession
        from api.models import Product
        
        product = Product.objects.filter(id=product_id).first()
        if product:
            session = None
            if session_id:
                session = ChatSession.objects.filter(id=session_id).first()
                
            RecommendationLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session=session,
                product=product,
                reason="Clicked from chat recommendation"
            )
            return JsonResponse({'status': 'click tracked', 'product_id': product_id})
    except Exception:
        pass
        
    return JsonResponse({'status': 'error'}, status=400)
