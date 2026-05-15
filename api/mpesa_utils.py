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
    """
    Fetch OAuth token from Safaricom.
    Returns (token, error_message).
    Retries once on transient failure.
    """
    key = getattr(settings, 'MPESA_CONSUMER_KEY', '').strip()
    secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '').strip()

    if not key or not secret:
        msg = (
            "M-Pesa credentials are not set. "
            "Add MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET to your Render environment variables."
        )
        print(f"[MPESA] CONFIG ERROR: {msg}")
        return None, msg

    url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    for attempt in range(1, 3):  # try twice
        try:
            res = requests.get(
                url,
                auth=(key, secret),
                timeout=12,
            )
            print(f"[MPESA] OAuth attempt {attempt}: HTTP {res.status_code}")

            if res.status_code == 200:
                token = res.json().get('access_token')
                if token:
                    return token, None
                return None, f"Safaricom returned 200 but no access_token: {res.json()}"

            # 400 = bad credentials (no point retrying)
            if res.status_code in (400, 401):
                detail = res.text[:300]
                return None, (
                    f"Safaricom rejected credentials (HTTP {res.status_code}). "
                    f"Check MPESA_CONSUMER_KEY / MPESA_CONSUMER_SECRET on Render. "
                    f"Detail: {detail}"
                )

            # 5xx → retry
            if attempt == 2:
                return None, f"Safaricom auth server error (HTTP {res.status_code}): {res.text[:200]}"

        except requests.Timeout:
            if attempt == 2:
                return None, "Safaricom OAuth timed out after 2 attempts"
            time.sleep(1)

        except Exception as e:
            return None, f"Safaricom auth exception: {str(e)}"

    return None, "Safaricom auth failed after retries"


def initiate_mpesa_payment(phone, amount, order_id):
    """
    Fire an STK Push.
    Returns the full Safaricom response dict on success,
    or {"error": "<human-readable message>"} on failure.
    """
    token, err = get_access_token()
    if not token:
        print(f"[MPESA] initiate_mpesa_payment: auth failed — {err}")
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
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        data = response.json()
        print(f"[MPESA] STK Push response (HTTP {response.status_code}): {data}")

        # Safaricom returns 200 even for some errors — check response body
        error_code = data.get('errorCode') or data.get('ResultCode')
        error_msg = data.get('errorMessage') or data.get('ResultDesc') or ''

        if response.status_code != 200 or (error_code and str(error_code) != '0'):
            friendly = _friendly_mpesa_error(str(error_code), error_msg)
            return {"error": friendly}

        return data

    except requests.Timeout:
        return {"error": "The STK Push request to Safaricom timed out. Please try again."}
    except Exception as e:
        print(f"[MPESA] STK Push exception: {e}")
        return {"error": f"M-Pesa request failed: {str(e)}"}


def verify_mpesa_payment(checkout_request_id):
    """
    Query the STK Push status.
    Returns the Safaricom response dict.
    On transient 'not found yet', returns {"ResultCode": "pending"} so the
    frontend keeps polling rather than treating it as a hard failure.
    """
    token, err = get_access_token()
    if not token:
        print(f"[MPESA] verify_mpesa_payment: auth failed — {err}")
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
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        data = response.json()
        print(f"[MPESA] Verify response (HTTP {response.status_code}): {data}")

        # "The transaction is being processed" → still pending, not a real error
        result_code = str(data.get('ResultCode', ''))
        result_desc = data.get('ResultDesc', '')

        PENDING_PHRASES = [
            'being processed',
            'transaction not found',
            'in process',
            'request cancelled',   # user hasn't responded yet
        ]
        if any(p in result_desc.lower() for p in PENDING_PHRASES):
            return {"ResultCode": "pending", "ResultDesc": result_desc}

        return data

    except requests.Timeout:
        # Treat timeout as still-pending so the frontend keeps polling
        return {"ResultCode": "pending", "ResultDesc": "Verify request timed out, still polling"}
    except Exception as e:
        print(f"[MPESA] Verify exception: {e}")
        return {"error": f"Verify error: {str(e)}"}


def _friendly_mpesa_error(code: str, desc: str) -> str:
    """Map Safaricom error codes to user-friendly messages."""
    mapping = {
        '17': "M-Pesa limit exceeded. Try a smaller amount or try again later.",
        '1': "Payment was rejected or insufficient balance.",
        '1032': "Payment request cancelled by user.",
        '1037': "STK Push timed out — user did not respond. Please try again.",
        '2001': "Wrong M-Pesa PIN entered.",
        '400.002.02': "Bad request sent to Safaricom. Contact support.",
        '404.001.04': "Invalid shortcode configuration. Contact support.",
    }
    if code in mapping:
        return mapping[code]
    if desc:
        return f"M-Pesa error: {desc}"
    return "M-Pesa payment failed. Please try again."