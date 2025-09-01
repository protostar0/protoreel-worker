import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class PostmarkEmailService:
    """Email service using Postmark API"""
    
    def __init__(self):
        self.api_token = os.environ.get("POSTMARK_API_TOKEN")
        self.from_email = os.environ.get("MAIL_FROM", "support@protoreel.com")
        self.base_url = "https://api.postmarkapp.com"
        
        if not self.api_token:
            logger.warning("POSTMARK_API_TOKEN not configured")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        message_stream: str = "outbound"
    ) -> Dict[str, Any]:
        """
        Send email using Postmark API
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
            message_stream: Message stream (default: outbound)
            
        Returns:
            Dict containing response data
        """
        if not self.api_token:
            raise Exception("POSTMARK_API_TOKEN not configured")
        
        payload = {
            "From": self.from_email,
            "To": to_email,
            "Subject": subject,
            "HtmlBody": html_content,
            "MessageStream": message_stream
        }
        
        # Add text content if provided
        if text_content:
            payload["TextBody"] = text_content
        
        try:
            response = requests.post(
                f"{self.base_url}/email",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Postmark-Server-Token": self.api_token
                },
                json=payload,
                timeout=30
            )
            
            response_data = response.json()
            
            if response.status_code == 200:
                logger.info(f"Postmark email sent successfully to {to_email}. MessageID: {response_data.get('MessageID')}")
                return {
                    "success": True,
                    "message_id": response_data.get("MessageID"),
                    "status_code": response.status_code,
                    "response": response_data
                }
            else:
                error_msg = f"Postmark API error: {response.status_code} - {response_data.get('Message', 'Unknown error')}"
                logger.error(f"{error_msg} for {to_email}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                    "response": response_data
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Postmark request failed: {str(e)}"
            logger.error(f"{error_msg} for {to_email}")
            return {
                "success": False,
                "error": error_msg,
                "status_code": None,
                "response": None
            }
        except Exception as e:
            error_msg = f"Unexpected error sending email: {str(e)}"
            logger.error(f"{error_msg} for {to_email}")
            return {
                "success": False,
                "error": error_msg,
                "status_code": None,
                "response": None
            }
    
# Global email service instance
email_service = PostmarkEmailService() 