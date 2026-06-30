from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def compress_memory_task(session_id: int):
    """
    Celery task to compress the memory of a chat session in the background.
    """
    try:
        from .services.memory_service import compress_memory
        compress_memory(session_id)
    except Exception as e:
        logger.error(f"Failed to compress memory for session {session_id}: {e}")

