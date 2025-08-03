#!/usr/bin/env python3
"""
Simple email test script to verify Gmail SMTP configuration
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email():
    # Get environment variables
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD') 
    admin_email = os.getenv('ADMIN_EMAIL')
    
    print(f"SMTP Username: {smtp_username}")
    print(f"Admin Email: {admin_email}")
    print(f"Password set: {'Yes' if smtp_password else 'No'}")
    
    if not smtp_username or not smtp_password or not admin_email:
        print("❌ Missing email configuration!")
        print("Please set SMTP_USERNAME, SMTP_PASSWORD, and ADMIN_EMAIL environment variables")
        return False
    
    # Test SMTP connection
    smtp_server = "smtp.gmail.com"
    
    # Try port 465 (SSL) first
    print("\n🔄 Testing SMTP SSL (port 465)...")
    try:
        with smtplib.SMTP_SSL(smtp_server, 465) as server:
            print("✅ Connected to Gmail SMTP SSL")
            server.login(smtp_username, smtp_password)
            print("✅ Authentication successful")
            
            # Send test email
            message = MIMEMultipart()
            message["Subject"] = "Test Email - Afro Nyanka Tours"
            message["From"] = smtp_username
            message["To"] = admin_email
            
            html_content = """
            <html>
            <body>
                <h2>✅ Email Test Successful</h2>
                <p>This is a test email to verify Gmail SMTP configuration is working.</p>
                <p>Configuration details:</p>
                <ul>
                    <li>SMTP Server: smtp.gmail.com:465 (SSL)</li>
                    <li>From: {}</li>
                    <li>To: {}</li>
                </ul>
            </body>
            </html>
            """.format(smtp_username, admin_email)
            
            message.attach(MIMEText(html_content, "html"))
            server.sendmail(smtp_username, admin_email, message.as_string())
            print("✅ Test email sent successfully via SSL!")
            return True
            
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")
    
    # Try port 587 (STARTTLS) as fallback
    print("\n🔄 Testing SMTP STARTTLS (port 587)...")
    try:
        with smtplib.SMTP(smtp_server, 587) as server:
            print("✅ Connected to Gmail SMTP")
            server.starttls()
            print("✅ STARTTLS successful")
            server.login(smtp_username, smtp_password)
            print("✅ Authentication successful")
            
            # Send test email
            message = MIMEMultipart()
            message["Subject"] = "Test Email - Afro Nyanka Tours (STARTTLS)"
            message["From"] = smtp_username
            message["To"] = admin_email
            
            html_content = """
            <html>
            <body>
                <h2>✅ Email Test Successful</h2>
                <p>This is a test email to verify Gmail SMTP configuration is working.</p>
                <p>Configuration details:</p>
                <ul>
                    <li>SMTP Server: smtp.gmail.com:587 (STARTTLS)</li>
                    <li>From: {}</li>
                    <li>To: {}</li>
                </ul>
            </body>
            </html>
            """.format(smtp_username, admin_email)
            
            message.attach(MIMEText(html_content, "html"))
            server.sendmail(smtp_username, admin_email, message.as_string())
            print("✅ Test email sent successfully via STARTTLS!")
            return True
            
    except Exception as e:
        print(f"❌ STARTTLS connection failed: {e}")
    
    print("\n❌ Both SMTP methods failed!")
    print("\n🔧 Troubleshooting tips:")
    print("1. Make sure 2-Factor Authentication is enabled on your Gmail account")
    print("2. Generate an App Password (not your regular Gmail password)")
    print("3. Use the App Password in SMTP_PASSWORD environment variable")
    print("4. Check that your Gmail account allows 'Less secure app access' (if not using App Password)")
    print("5. Verify your internet connection")
    
    return False

if __name__ == "__main__":
    print("🧪 Gmail SMTP Configuration Test")
    print("=" * 40)
    
    success = test_email()
    
    if success:
        print("\n🎉 Email configuration is working correctly!")
    else:
        print("\n💥 Email configuration needs to be fixed!")
        sys.exit(1)
