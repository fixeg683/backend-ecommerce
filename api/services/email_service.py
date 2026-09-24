import html
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_account_confirmation_email(*, to_email, user_name, token):
    """Send an account verification email through Resend."""
    frontend_url = settings.FRONTEND_URL.rstrip('/')
    confirmation_url = f'{frontend_url}/verify-email?token={token}'
    safe_name = html.escape(user_name or 'there')
    safe_url = html.escape(confirmation_url, quote=True)

    payload = {
        'from': settings.EMAIL_FROM,
        'reply_to': 'support@nexusmall.sbs',
        'to': [to_email],
        'subject': 'Confirm your Nexus Mall account',
        'html': f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 8px;">
          <h2 style="color: #111827; margin-bottom: 16px;">Welcome to Nexus Mall, {safe_name}!</h2>
          <p style="color: #4b5563; font-size: 15px; line-height: 1.5;">Thank you for creating an account with us. Please verify your email address to activate your account.</p>
          <div style="text-align: center; margin: 32px 0;">
            <a href="{safe_url}" style="background-color: #111827; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Verify Email Address</a>
          </div>
          <p style="color: #6b7280; font-size: 13px;">If the button doesn't work, copy and paste this link into your browser:<br/><a href="{safe_url}" style="color: #2563eb;">{safe_url}</a></p>
          <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;" />
          <p style="color: #9ca3af; font-size: 12px;">If you didn't create this account, you can safely ignore this email.</p>
        </div>
        ''',
    }

    try:
        response = requests.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {settings.RESEND_API_KEY}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return {'success': True, 'data': response.json()}
    except (requests.RequestException, ValueError) as error:
        logger.exception('Error sending confirmation email through Resend')
        return {'success': False, 'error': error}