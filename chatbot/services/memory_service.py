from asgiref.sync import sync_to_async
from chatbot.models import ChatSession, ChatMessage
import json
import logging

logger = logging.getLogger(__name__)

@sync_to_async
def get_chat_history(session_id: int):
    """
    Returns the chat history for the given session.
    Includes the rolling summary (if any) as a system message, plus recent messages.
    """
    session = ChatSession.objects.filter(id=session_id).first()
    if not session:
        return []

    messages = []
    
    # Inject summary if it exists
    if session.summary:
        messages.append({
            "role": "system", 
            "content": f"Previous conversation summary: {session.summary}"
        })
        
    # Get recent messages (e.g., last 10 messages)
    recent_qs = ChatMessage.objects.filter(session_id=session_id).order_by('-created_at')[:10]
    recent_messages = list(reversed(recent_qs))
    
    for msg in recent_messages:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })
        
    return messages

def compress_memory(session_id: int):
    """
    Compresses older messages into a rolling summary.
    This is meant to be called by a Celery task.
    """
    try:
        from openai import OpenAI
        from django.conf import settings
        
        session = ChatSession.objects.get(id=session_id)
        
        # Get all messages
        all_messages = list(ChatMessage.objects.filter(session=session).order_by('created_at'))
        
        # If less than 15 messages, don't compress yet
        if len(all_messages) < 15:
            return
            
        # Keep the last 5 messages, compress the rest
        messages_to_compress = all_messages[:-5]
        messages_to_keep = all_messages[-5:]
        
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            return
            
        client = OpenAI(api_key=api_key)
        
        conversation_text = ""
        for m in messages_to_compress:
            conversation_text += f"{m.role.capitalize()}: {m.content}\n"
            
        prompt = f"""
        You are an AI assistant helping to compress chat memory. 
        Below is a conversation between a User and an Assistant.
        The current summary of the conversation is: '{session.summary}'
        
        Here are the new messages to compress:
        {conversation_text}
        
        Please provide a new, concise summary of the entire conversation up to this point, capturing key details, user preferences, and important context.
        """
        
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": prompt}],
        )
        
        new_summary = response.choices[0].message.content
        
        # Update session
        session.summary = new_summary
        session.save()
        
        # Delete compressed messages to save space
        # (Be careful here: in some systems you might want to keep them but mark them as compressed. We will delete them as per standard rolling memory)
        message_ids_to_delete = [m.id for m in messages_to_compress]
        ChatMessage.objects.filter(id__in=message_ids_to_delete).delete()
        
    except Exception as e:
        logger.error(f"Error compressing memory for session {session_id}: {e}")
