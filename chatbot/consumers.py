import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_key = self.scope['url_route']['kwargs'].get('session_key', 'default')
        # Here we should get or create the session
        self.session_id, self.user_id = await self.get_or_create_session(self.session_key)
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or '{}')
        except json.JSONDecodeError:
            payload = {'message': text_data or ''}

        message = (payload.get('message') or '').strip()
        if not message:
            return

        if contains_prompt_injection(message):
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'Prompt injection blocked.'}))
            return

        # Save user message
        await self.save_message("user", message)

        try:
            from .services.openai_service import get_chat_stream
            
            # Start streaming response
            full_content = ""
            async for chunk in get_chat_stream(self.session_id, self.user_id, message):
                # The chunk is already a JSON string from the service
                await self.send(text_data=chunk)
                
                # Parse to save the assistant message later
                chunk_data = json.loads(chunk)
                if chunk_data.get("type") == "content":
                    full_content += chunk_data.get("content", "")
                elif chunk_data.get("type") == "message":
                    full_content = chunk_data.get("content", "")

            # Save assistant message
            if full_content:
                await self.save_message("assistant", full_content)

            # Trigger memory compression asynchronously
            try:
                from .tasks import compress_memory_task
                compress_memory_task.delay(self.session_id)
            except Exception as e:
                # Fallback if celery is not configured or running
                logger.warning(f"Could not dispatch celery task, running sync: {e}")
                from .services.memory_service import compress_memory
                await sync_to_async(compress_memory)(self.session_id)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'Sorry, I encountered an error processing your request.'}))

    async def disconnect(self, close_code):
        return None

    @sync_to_async
    def get_or_create_session(self, session_key: str):
        from .models import ChatSession
        
        # In a real app we might link this session_key to the user if authenticated
        user = self.scope.get('user')
        user_id = user.id if user and user.is_authenticated else None
        
        session, created = ChatSession.objects.get_or_create(
            title=session_key, # Using title as a temporary key holder for simplicity if needed, or we might need a session_key field
        )
        if user_id and not session.user_id:
            session.user_id = user_id
            session.save()
            
        return session.id, user_id
        
    @sync_to_async
    def save_message(self, role: str, content: str):
        from .models import ChatMessage
        ChatMessage.objects.create(
            session_id=self.session_id,
            role=role,
            content=content
        )


def contains_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    blocked_markers = ['ignore all previous instructions', 'system prompt', 'developer message']
    return any(marker in lowered for marker in blocked_markers)
