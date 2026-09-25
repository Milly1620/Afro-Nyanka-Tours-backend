#!/usr/bin/env python3
"""
Simple email test script to verify Brevo configuration.
Sends a test email to ADMIN_EMAIL using the app's EmailService.
"""

import sys

from src.core.config import settings
from src.services.email_service import EmailService


def test_email():
    print(f"Sender: {settings.sender_name} <{settings.sender_email}>")
    print(f"Admin Email: {settings.admin_email}")
    print(f"Brevo API key set: {'Yes' if settings.brevo_api_key else 'No'}")

    if not settings.brevo_api_key or not settings.admin_email:
        print("❌ Missing email configuration!")
        print("Please set BREVO_API_KEY and ADMIN_EMAIL environment variables")
        return False

    html = """
    <html>
      <body>
        <h2>✅ Email Test Successful</h2>
        <p>This is a test email to verify the Brevo configuration is working.</p>
      </body>
    </html>
    """
    ok = EmailService().send_email(settings.admin_email, "Test Email - Afro Nyanka Tours", html)
    print("✅ Test email sent successfully!" if ok else "❌ Failed to send test email - check the logs above")
    return ok


if __name__ == "__main__":
    sys.exit(0 if test_email() else 1)
