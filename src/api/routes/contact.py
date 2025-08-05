from fastapi import APIRouter, BackgroundTasks, HTTPException
from src.schemas.schemas import ContactForm, ContactResponse
from src.services.email_service import email_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ContactResponse)
def send_contact_email(
    contact_form: ContactForm, 
    background_tasks: BackgroundTasks
):
    """
    Send contact form email to admin
    
    This endpoint allows users to send messages to the admin team.
    The email will be sent in the background to avoid blocking the response.
    """
    try:
        # Validate email service configuration
        if not email_service.admin_email:
            logger.error("Admin email not configured")
            raise HTTPException(
                status_code=500, 
                detail="Contact form is temporarily unavailable. Please try again later."
            )
        
        # Send email in background to avoid blocking the response
        background_tasks.add_task(
            email_service.send_contact_form_email,
            contact_form.name,
            contact_form.email,
            contact_form.subject,
            contact_form.message
        )
        
        logger.info(f"Contact form submitted by {contact_form.name} ({contact_form.email})")
        
        return ContactResponse(
            message="Your message has been sent successfully! We'll get back to you soon.",
            success=True
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing contact form: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send your message. Please try again later."
        )


@router.post("/test", response_model=ContactResponse)
def test_contact_email():
    """
    Test contact form email functionality (for development/testing)
    """
    try:
        test_form = ContactForm(
            name="Test User",
            email="test@example.com",
            subject="Test Contact Form",
            message="This is a test message to verify the contact form functionality is working correctly."
        )
        
        result = email_service.send_contact_form_email(
            test_form.name,
            test_form.email,
            test_form.subject,
            test_form.message
        )
        
        if result:
            return ContactResponse(
                message="Test contact email sent successfully!",
                success=True
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Test email failed to send. Check email configuration."
            )
    
    except Exception as e:
        logger.error(f"Test contact email failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}"
        )
