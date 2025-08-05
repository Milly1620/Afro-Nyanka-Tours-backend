import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from src.core.config import settings
from src.schemas.schemas import Booking
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.admin_email = settings.admin_email

    def send_email(self, to_email: str, subject: str, html_content: str):
        """Send email using Gmail SMTP"""
        try:
            # Check if email configuration is properly set
            if not self.smtp_username or not self.smtp_password:
                logger.error("Email configuration missing: SMTP_USERNAME or SMTP_PASSWORD not set")
                return False
            
            if not self.admin_email:
                logger.error("Admin email not configured")
                return False
            
            logger.info(f"Attempting to send email to {to_email}")
            logger.info(f"Using SMTP server: {self.smtp_server}:{self.smtp_port}")
            logger.info(f"SMTP username: {self.smtp_username}")
            
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.smtp_username
            message["To"] = to_email

            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Try with SMTP_SSL first (port 465), then fallback to STARTTLS (port 587)
            try:
                # Use SMTP_SSL for port 465
                if self.smtp_port == 465:
                    logger.info("Using SMTP_SSL on port 465...")
                    with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                        server.set_debuglevel(0)  # Disable debug to reduce noise
                        logger.info("Logging in...")
                        server.login(self.smtp_username, self.smtp_password)
                        logger.info("Sending email...")
                        server.sendmail(self.smtp_username, to_email, message.as_string())
                else:
                    # Use STARTTLS for port 587
                    logger.info("Using STARTTLS on port 587...")
                    with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                        server.set_debuglevel(0)  # Disable debug to reduce noise
                        logger.info("Starting TLS...")
                        server.starttls()
                        logger.info("Logging in...")
                        server.login(self.smtp_username, self.smtp_password)
                        logger.info("Sending email...")
                        server.sendmail(self.smtp_username, to_email, message.as_string())
                        
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"SMTP Authentication failed: {str(e)}")
                logger.error("Please check your Gmail App Password. Make sure 2FA is enabled and you're using an App Password, not your regular password.")
                return False
            except smtplib.SMTPConnectError as e:
                logger.error(f"SMTP Connection failed: {str(e)}")
                logger.error("Cannot connect to Gmail SMTP server. Check your internet connection.")
                return False
            except smtplib.SMTPServerDisconnected as e:
                logger.error(f"SMTP Server disconnected: {str(e)}")
                return False
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {str(e)}")
            return False

    def send_booking_confirmation(self, booking: Booking, booking_summary: dict):
        """Send booking confirmation email to customer"""
        subject = f"Multi-Tour Booking Confirmation - {len(booking.booking_tours)} Tours Selected"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; }
                .header { background-color: #2E8B57; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; border: 1px solid #ddd; }
                .booking-details { background-color: #f9f9f9; padding: 15px; margin: 15px 0; }
                .tour-section { margin: 20px 0; padding: 15px; border-left: 4px solid #2E8B57; background-color: #f8f9fa; }
                .location-list { margin: 10px 0; padding-left: 20px; }
                .location-item { margin: 5px 0; }
                .footer { text-align: center; padding: 20px; color: #666; }
                .summary-stats { display: flex; justify-content: space-around; margin: 20px 0; }
                .stat { text-align: center; }
                .stat-number { font-size: 24px; font-weight: bold; color: #2E8B57; }
                .stat-label { font-size: 14px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Afro Nyanka Tours</h1>
                    <h2>Multi-Tour Booking Confirmation</h2>
                </div>
                <div class="content">
                    <p>Dear {{ customer_name }},</p>
                    <p>Thank you for your exciting multi-tour booking with Afro Nyanka Tours! Your personalized travel experience has been received and is being processed.</p>
                    
                    <div class="summary-stats">
                        <div class="stat">
                            <div class="stat-number">{{ total_tours }}</div>
                            <div class="stat-label">Tours Selected</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ total_locations }}</div>
                            <div class="stat-label">Locations</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ number_of_people }}</div>
                            <div class="stat-label">People</div>
                        </div>
                    </div>
                    
                    <div class="booking-details">
                        <h3>Customer Details:</h3>
                        <p><strong>Preferred Date:</strong> {{ preferred_date }}</p>
                        {% if customer_age %}
                        <p><strong>Age:</strong> {{ customer_age }}</p>
                        {% endif %}
                        {% if additional_services %}
                        <p><strong>Additional Services:</strong> {{ additional_services }}</p>
                        {% endif %}
                    </div>
                    
                    <h3>Your Selected Tours & Locations:</h3>
                    {% for tour in tours_and_locations %}
                    <div class="tour-section">
                        <h4>{{ loop.index }}. {{ tour.tour_name }} ({{ tour.country }})</h4>
                        <p><em>{{ tour.region }}</em></p>
                        <div class="location-list">
                            <strong>Selected Locations:</strong>
                            {% for location in tour.selected_locations %}
                            <div class="location-item">• {{ location.location_name }}</div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                    
                    <p>We will contact you shortly to confirm your booking and provide a detailed itinerary for your multi-tour experience.</p>
                    <p>If you have any questions, please don't hesitate to contact us.</p>
                </div>
                <div class="footer">
                    <p>Best regards,<br>Afro Nyanka Tours Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            customer_name=booking.customer_name,
            preferred_date=booking.preferred_date.strftime("%B %d, %Y") if booking.preferred_date else "To be confirmed",
            customer_age=booking.customer_age,
            additional_services=booking.additional_services,
            number_of_people=booking.number_of_people,
            total_tours=booking_summary["total_tours"],
            total_locations=booking_summary["total_locations"],
            tours_and_locations=booking_summary["tours_and_locations"]
        )
        
        return self.send_email(booking.customer_email, subject, html_content)

    def send_admin_notification(self, booking: Booking, booking_summary: dict):
        """Send booking notification email to admin"""
        subject = f"New Multi-Tour Booking - {booking.customer_name} ({len(booking.booking_tours)} tours)"
        
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Multi-Tour Booking Notification</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f8f9fa;
                    margin: 0;
                    padding: 20px;
                }
                
                .container {
                    max-width: 650px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }
                
                .header {
                    background: #2563eb;
                    color: white;
                    padding: 24px;
                    text-align: center;
                }
                
                .header h1 {
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                }
                
                .stats-bar {
                    background: #f1f5f9;
                    padding: 24px;
                    display: flex;
                    justify-content: center;
                    gap: 60px;
                    border-bottom: 1px solid #e2e8f0;
                }
                
                .stat {
                    text-align: center;
                    min-width: 120px;
                }
                
                .stat-number {
                    font-size: 28px;
                    font-weight: 700;
                    color: #2563eb;
                    line-height: 1;
                    margin-bottom: 8px;
                }
                
                .stat-label {
                    font-size: 14px;
                    color: #64748b;
                    font-weight: 500;
                }
                
                .content {
                    padding: 32px;
                }
                
                .section {
                    margin-bottom: 32px;
                }
                
                .section:last-child {
                    margin-bottom: 0;
                }
                
                .section-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #1f2937;
                    margin-bottom: 16px;
                    padding-bottom: 8px;
                    border-bottom: 2px solid #e5e7eb;
                }
                
                .info-row {
                    display: flex;
                    padding: 10px 0;
                    border-bottom: 1px solid #f3f4f6;
                }
                
                .info-row:last-child {
                    border-bottom: none;
                }
                
                .info-label {
                    font-weight: 500;
                    color: #6b7280;
                    width: 140px;
                    flex-shrink: 0;
                }
                
                .info-value {
                    color: #1f2937;
                    font-weight: 500;
                }
                
                .tour-card {
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 16px;
                }
                
                .tour-card:last-child {
                    margin-bottom: 0;
                }
                
                .tour-header {
                    margin-bottom: 16px;
                }
                
                .tour-title {
                    font-size: 16px;
                    font-weight: 600;
                    color: #1f2937;
                    margin-bottom: 4px;
                }
                
                .tour-location {
                    color: #6b7280;
                    font-size: 14px;
                }
                
                .locations-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 8px;
                    margin-top: 12px;
                }
                
                .location-item {
                    background: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    border: 1px solid #e2e8f0;
                    font-size: 14px;
                    color: #374151;
                }
                
                .location-count {
                    font-size: 13px;
                    color: #6b7280;
                    margin-bottom: 8px;
                }
                
                .footer {
                    background: #f9fafb;
                    padding: 20px 32px;
                    border-top: 1px solid #e5e7eb;
                    font-size: 14px;
                    color: #6b7280;
                    text-align: center;
                }
                
                @media (max-width: 600px) {
                    body {
                        padding: 10px;
                    }
                    
                    .content {
                        padding: 24px;
                    }
                    
                    .stats-bar {
                        gap: 20px;
                        padding: 16px;
                    }
                    
                    .info-row {
                        flex-direction: column;
                        gap: 4px;
                    }
                    
                    .info-label {
                        width: auto;
                        font-size: 14px;
                    }
                    
                    .locations-grid {
                        grid-template-columns: 1fr;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Multi-Tour Booking Received</h1>
                </div>
                
                <div class="stats-bar">
                    <div class="stat">
                        <div class="stat-number">{{ total_tours }}</div>
                        <div class="stat-label">Tours Selected</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{{ total_locations }}</div>
                        <div class="stat-label">Total Locations</div>
                    </div>
                </div>
                
                <div class="content">
                    <div class="section">
                        <h2 class="section-title">Customer Details</h2>
                        <div class="info-row">
                            <span class="info-label">Name</span>
                            <span class="info-value">{{ customer_name }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Email</span>
                            <span class="info-value">{{ customer_email }}</span>
                        </div>
                        {% if customer_age %}
                        <div class="info-row">
                            <span class="info-label">Age</span>
                            <span class="info-value">{{ customer_age }}</span>
                        </div>
                        {% endif %}
                        <div class="info-row">
                            <span class="info-label">Country</span>
                            <span class="info-value">{{ customer_country }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Number of People</span>
                            <span class="info-value">{{ number_of_people }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Preferred Date</span>
                            <span class="info-value">{{ preferred_date }}</span>
                        </div>
                        {% if additional_services %}
                        <div class="info-row">
                            <span class="info-label">Additional Services</span>
                            <span class="info-value">{{ additional_services }}</span>
                        </div>
                        {% endif %}
                    </div>
                    
                    <div class="section">
                        <h2 class="section-title">Selected Tours</h2>
                        {% for tour in tours_and_locations %}
                        <div class="tour-card">
                            <div class="tour-header">
                                <div class="tour-title">{{ loop.index }}. {{ tour.tour_name }}</div>
                                <div class="tour-location">{{ tour.country }} • {{ tour.region }}</div>
                            </div>
                            <div class="location-count">{{ tour.selected_locations|length }} locations selected:</div>
                            <div class="locations-grid">
                                {% for location in tour.selected_locations %}
                                <div class="location-item">{{ location.location_name }}</div>
                                {% endfor %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="footer">
                    Booking received on {{ current_time }}
                </div>
            </div>
        </body>
        </html>
        """
        
        from datetime import datetime
        
        template = Template(html_template)
        html_content = template.render(
            customer_name=booking.customer_name,
            customer_email=booking.customer_email,
            customer_age=booking.customer_age,
            customer_country=booking.customer_country or "Not provided",
            preferred_date=booking.preferred_date.strftime("%B %d, %Y") if booking.preferred_date else "Not specified",
            additional_services=booking.additional_services,
            number_of_people=booking.number_of_people,
            total_tours=booking_summary["total_tours"],
            total_locations=booking_summary["total_locations"],
            tours_and_locations=booking_summary["tours_and_locations"],
            current_time=datetime.now().strftime("%B %d, %Y at %I:%M %p")
        )
        
        return self.send_email(self.admin_email, subject, html_content)

    def send_contact_form_email(self, name: str, email: str, subject: str, message: str):
        """Send contact form email to admin"""
        admin_subject = f"Contact Form: {subject}"
        
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Contact Form Submission</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f8f9fa;
                    margin: 0;
                    padding: 20px;
                }
                
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }
                
                .header {
                    background: #2E8B57;
                    color: white;
                    padding: 24px;
                    text-align: center;
                }
                
                .header h1 {
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                }
                
                .content {
                    padding: 32px;
                }
                
                .contact-info {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 6px;
                    margin-bottom: 24px;
                    border-left: 4px solid #2E8B57;
                }
                
                .info-row {
                    display: flex;
                    margin-bottom: 12px;
                    align-items: center;
                }
                
                .info-label {
                    font-weight: 600;
                    color: #2E8B57;
                    min-width: 80px;
                    margin-right: 16px;
                }
                
                .info-value {
                    color: #333;
                }
                
                .message-section {
                    margin-top: 24px;
                }
                
                .message-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #2E8B57;
                    margin-bottom: 16px;
                    border-bottom: 2px solid #e2e8f0;
                    padding-bottom: 8px;
                }
                
                .message-content {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 6px;
                    border: 1px solid #e2e8f0;
                    white-space: pre-wrap;
                    font-size: 15px;
                    line-height: 1.6;
                }
                
                .footer {
                    background: #f1f5f9;
                    padding: 20px;
                    text-align: center;
                    color: #64748b;
                    font-size: 14px;
                }
                
                .reply-button {
                    display: inline-block;
                    background: #2E8B57;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin-top: 16px;
                }
                
                .timestamp {
                    color: #64748b;
                    font-size: 14px;
                    margin-top: 16px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌍 Afro Nyanka Tours</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9;">New Contact Form Submission</p>
                </div>
                
                <div class="content">
                    <div class="contact-info">
                        <div class="info-row">
                            <span class="info-label">Name:</span>
                            <span class="info-value">{{ name }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Email:</span>
                            <span class="info-value">{{ email }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Subject:</span>
                            <span class="info-value">{{ subject }}</span>
                        </div>
                    </div>
                    
                    <div class="message-section">
                        <div class="message-title">Message:</div>
                        <div class="message-content">{{ message }}</div>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="mailto:{{ email }}?subject=Re: {{ subject }}" class="reply-button">
                            Reply to {{ name }}
                        </a>
                    </div>
                    
                    <div class="timestamp">
                        Received on {{ current_time }}
                    </div>
                </div>
                
                <div class="footer">
                    <p>This message was sent through the Afro Nyanka Tours contact form.</p>
                    <p>Please respond to the customer's inquiry as soon as possible.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            name=name,
            email=email,
            subject=subject,
            message=message,
            current_time=datetime.now().strftime("%B %d, %Y at %I:%M %p")
        )
        
        return self.send_email(self.admin_email, admin_subject, html_content)


email_service = EmailService()
