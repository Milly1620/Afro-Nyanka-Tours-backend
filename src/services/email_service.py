import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from src.core.config import settings
from src.schemas.schemas import Booking
import logging

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
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.smtp_username
            message["To"] = to_email

            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.smtp_username, to_email, message.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_booking_confirmation(self, booking: Booking):
        """Send booking confirmation email to customer"""
        subject = f"Booking Confirmation - {booking.tour.name}"
        
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
                .footer { text-align: center; padding: 20px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Afro Nyanka Tours</h1>
                    <h2>Booking Confirmation</h2>
                </div>
                <div class="content">
                    <p>Dear {{ customer_name }},</p>
                    <p>Thank you for booking with Afro Nyanka Tours! Your booking has been received and is being processed.</p>
                    
                    <div class="booking-details">
                        <h3>Booking Details:</h3>
                        <p><strong>Tour:</strong> {{ tour_name }}</p>
                        <p><strong>Country:</strong> {{ tour_country }}</p>
                        <p><strong>Preferred Date:</strong> {{ preferred_date }}</p>
                        {% if customer_age %}
                        <p><strong>Age:</strong> {{ customer_age }}</p>
                        {% endif %}
                        {% if additional_services %}
                        <p><strong>Additional Services:</strong> {{ additional_services }}</p>
                        {% endif %}
                    </div>
                    
                    <p>We will contact you shortly to confirm your booking and provide further details.</p>
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
            tour_name=booking.tour.name,
            tour_country=booking.tour.country,
            preferred_date=booking.preferred_date.strftime("%B %d, %Y") if booking.preferred_date else "To be confirmed",
            customer_age=booking.customer_age,
            additional_services=booking.additional_services
        )
        
        return self.send_email(booking.customer_email, subject, html_content)

    def send_admin_notification(self, booking: Booking):
        """Send booking notification email to admin"""
        subject = f"New Booking Received - {booking.customer_name}"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; }
                .header { background-color: #FF6B35; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; border: 1px solid #ddd; }
                .booking-details { background-color: #f9f9f9; padding: 15px; margin: 15px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Booking Alert</h1>
                </div>
                <div class="content">
                    <p>A new booking has been received:</p>
                    
                    <div class="booking-details">
                        <h3>Customer Information:</h3>
                        <p><strong>Name:</strong> {{ customer_name }}</p>
                        <p><strong>Email:</strong> {{ customer_email }}</p>
                        {% if customer_age %}
                        <p><strong>Age:</strong> {{ customer_age }}</p>
                        {% endif %}
                        <p><strong>Country:</strong> {{ customer_country }}</p>
                        
                        <h3>Booking Details:</h3>
                        <p><strong>Tour:</strong> {{ tour_name }}</p>
                        <p><strong>Tour Country:</strong> {{ tour_country }}</p>
                        <p><strong>Preferred Date:</strong> {{ preferred_date }}</p>
                        {% if additional_services %}
                        <p><strong>Additional Services:</strong> {{ additional_services }}</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            customer_name=booking.customer_name,
            customer_email=booking.customer_email,
            customer_age=booking.customer_age,
            customer_country=booking.customer_country or "Not provided",
            tour_name=booking.tour.name,
            tour_country=booking.tour.country,
            preferred_date=booking.preferred_date.strftime("%B %d, %Y") if booking.preferred_date else "Not specified",
            additional_services=booking.additional_services
        )
        
        return self.send_email(self.admin_email, subject, html_content)


email_service = EmailService()
