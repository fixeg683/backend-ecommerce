import requests
import base64
from datetime import datetime
from django.conf import settings

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        res = requests.get(url, auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET))
        res.raise_for_status()
        return res.json().get('access_token')
    except Exception as e:
        print(f"Error getting M-Pesa token: {e}")
        return None

# Rename this or alias it to match your views.py import
def initiate_mpesa_payment(phone, amount, order_id):
    token = get_access_token()
    if not token:
        return {"error": "Could not authenticate with Safaricom"}

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()
    
    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": f"{settings.BASE_URL}/api/payments/callback/",
        "AccountReference": f"INV{order_id}",
        "TransactionDesc": "Ecom Payment"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", 
            json=payload, 
            headers=headers
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# Added this to prevent the "cannot import verify_mpesa_payment" error
def verify_mpesa_payment(checkout_request_id):
    """
    Placeholder for M-Pesa Query request to check status
    """
    token = get_access_token()
    # Add Daraja Query logic here if needed
    return {"status": "Processing"}