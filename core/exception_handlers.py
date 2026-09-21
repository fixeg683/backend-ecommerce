import logging

from django.db import OperationalError, InterfaceError
from rest_framework.views import exception_handler as drf_default_exception_handler
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler so that database connectivity
    failures (e.g. the Supabase pooler being paused/unreachable) return a
    clean, predictable JSON error instead of an unhandled 500 with a raw
    psycopg2/Django traceback leaking to API clients.
    """
    response = drf_default_exception_handler(exc, context)

    if response is not None:
        return response

    if isinstance(exc, (OperationalError, InterfaceError)):
        view = context.get('view')
        logger.error(
            "[DB UNAVAILABLE] %s.%s — %s",
            view.__class__.__name__ if view else "unknown_view",
            context.get('request').method if context.get('request') else "?",
            exc,
        )
        return Response(
            {
                "error": "Service temporarily unavailable. Please try again shortly.",
                "detail": "database_unreachable",
            },
            status=503,
        )

    logger.error("[UNHANDLED API ERROR] %s", exc, exc_info=True)
    return None