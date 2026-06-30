import requests
import base64
import time
from datetime import datetime
from django.conf import settings


def format_phone(phone):
    """Normalise phone to 254XXXXXXXXX format."""
    phone = str(phone).strip().replace(' ', '').replace('+', '')
    if phone.startswith('254'):
        return phone
    if phone.startswith('0'):
        return '254' + phone[1:]
    return phone


def _make_password(timestamp: str) -> str:
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


def get_access_token():
    """Fetch OAuth token from Safaricom. Returns (token, error_message)."""
    if not settings.MPESA_CONSUMER_KEY or not settings.MPESA_CONSUMER_SECRET:
        return None, "M-Pesa credentials not configured on server"

    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        res = requests.get(
            url,
            auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            timeout=10
        )
        if res.status_code != 200:
            return None, f"Safaricom auth failed ({res.status_code}): {res.text[:200]}"

        token = res.json().get('access_token')
        if not token:
            return None, f"No access_token in Safaricom response: {res.json()}"

        return token, None

    except requests.Timeout:
        return None, "Safaricom auth request timed out"
    except Exception as e:
        return None, f"Safaricom auth error: {str(e)}"


def initiate_mpesa_payment(phone, amount, order_id):
    token, err = get_access_token()
    if not token:
        print(f"[MPESA] Auth failed: {err}")
        return {"error": err}

    phone = format_phone(str(phone))
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = _make_password(timestamp)

    callback_url = f"{settings.BASE_URL.rstrip('/')}/api/payments/callback/"

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": f"Order{order_id}",
        "TransactionDesc": f"Payment for order {order_id}",
    }

    print(f"[MPESA] STK Push → phone={phone}, amount={amount}, order={order_id}, callback={callback_url}")

    try:
        response = requests.post(
            "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=15
        )
        data = response.json()
        print(f"[MPESA] STK Push response: {data}")

        # Surface Safaricom-level errors
        if response.status_code != 200 or data.get('errorCode'):
            return {"error": data.get('errorMessage') or data.get('ResultDesc') or str(data)}

        return data

    except requests.Timeout:
        return {"error": "STK Push request to Safaricom timed out"}
    except Exception as e:
        return {"error": f"STK Push error: {str(e)}"}


def verify_mpesa_payment(checkout_request_id):
    token, err = get_access_token()
    if not token:
        print(f"[MPESA] Auth failed during verify: {err}")
        return {"error": err}

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = _make_password(timestamp)

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    try:
        response = requests.post(
            "https://api.safaricom.co.ke/mpesa/stkpush/v1/querystatus",
            json=payload,
            headers=headers,
            timeout=15
        )
        data = response.json()
        print(f"[MPESA] Verify response: {data}")
        return data

    except requests.Timeout:
        return {"error": "Verify request to Safaricom timed out"}
    except Exception as e:
        return {"error": f"Verify error: {str(e)}"}