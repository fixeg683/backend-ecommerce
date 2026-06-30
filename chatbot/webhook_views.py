import hashlib
import hmac
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def whatsapp_webhook(request):
    signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
    expected = os.getenv('WHATSAPP_WEBHOOK_SECRET', '')
    if expected and signature:
        digest = hmac.new(expected.encode('utf-8'), request.body, hashlib.sha256).hexdigest()
        if f'sha256={digest}' != signature:
            return JsonResponse({'status': 'invalid signature'}, status=403)
    return JsonResponse({'status': 'ok'})


@csrf_exempt
def instagram_webhook(request):
    signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
    expected = os.getenv('INSTAGRAM_WEBHOOK_SECRET', '')
    if expected and signature:
        digest = hmac.new(expected.encode('utf-8'), request.body, hashlib.sha256).hexdigest()
        if f'sha256={digest}' != signature:
            return JsonResponse({'status': 'invalid signature'}, status=403)
    return JsonResponse({'status': 'ok'})
