"""
Email service for sending booking confirmations
Uses SMTP with Gmail app password
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.config import config

logger = logging.getLogger(__name__)


class EmailService:
    """SMTP email service for sending booking confirmations"""
    
    def __init__(self):
        self.smtp_server = config.smtp_server
        self.smtp_port = config.smtp_port
        self.sender_email = config.smtp_email
        self.sender_password = config.smtp_password
        self.clinic_name = config.clinic_name
        self.clinic_phone = config.clinic_phone
        self.clinic_address = config.clinic_address
    
    def _create_confirmation_email(
        self,
        customer_name: str,
        booking_id: int,
        booking_type: str,
        date: str,
        time: str,
        notes: str = None
    ) -> Tuple[str, str]:
        """
        Create HTML email content for booking confirmation
        Returns: (subject, html_body)
        """
        subject = f"✅ Appointment Confirmed - {self.clinic_name} (Booking #{booking_id})"
        
        notes_section = ""
        if notes:
            notes_section = f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Notes:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{notes}</td>
            </tr>
            """
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">🏥 {self.clinic_name}</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Appointment Confirmation</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 30px;">
                    <p style="font-size: 18px; color: #333;">Dear <strong>{customer_name}</strong>,</p>
                    
                    <p style="color: #666; line-height: 1.6;">
                        Your appointment has been successfully confirmed! Here are your booking details:
                    </p>
                    
                    <!-- Booking Details -->
                    <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Booking ID:</strong></td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee; color: #667eea; font-weight: bold;">#{booking_id}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Appointment Type:</strong></td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">{booking_type}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">📅 {date}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Time:</strong></td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">🕐 {time}</td>
                            </tr>
                            {notes_section}
                        </table>
                    </div>
                    
                    <!-- Important Info -->
                    <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                        <p style="margin: 0; color: #856404;">
                            <strong>📌 Important:</strong> Please arrive 10-15 minutes before your scheduled appointment time. 
                            Bring a valid ID and any relevant medical records.
                        </p>
                    </div>
                    
                    <!-- Contact Info -->
                    <p style="color: #666; line-height: 1.6;">
                        If you need to reschedule or cancel, please contact us at least 24 hours in advance.
                    </p>
                    
                    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p style="margin: 5px 0; color: #666;">📍 {self.clinic_address}</p>
                        <p style="margin: 5px 0; color: #666;">📞 {self.clinic_phone}</p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #eee;">
                    <p style="margin: 0; color: #999; font-size: 12px;">
                        This is an automated confirmation email. Please do not reply directly to this email.
                    </p>
                    <p style="margin: 10px 0 0 0; color: #999; font-size: 12px;">
                        © 2026 {self.clinic_name}. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_body
    
    def send_booking_confirmation(
        self,
        to_email: str,
        customer_name: str,
        booking_id: int,
        booking_type: str,
        date: str,
        time: str,
        notes: str = None
    ) -> Tuple[bool, str]:
        """
        Send a booking confirmation email
        Returns: (success, error_message)
        """
        try:
            # Validate email configuration
            if not self.sender_email or not self.sender_password:
                logger.error("Email configuration missing")
                return False, "Email service not configured"
            
            # Create email content
            subject, html_body = self._create_confirmation_email(
                customer_name, booking_id, booking_type, date, time, notes
            )
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.clinic_name} <{self.sender_email}>"
            message["To"] = to_email
            
            # Add plain text fallback
            plain_text = f"""
            Appointment Confirmed - {self.clinic_name}
            
            Dear {customer_name},
            
            Your appointment has been confirmed.
            
            Booking ID: #{booking_id}
            Appointment Type: {booking_type}
            Date: {date}
            Time: {time}
            
            Please arrive 10-15 minutes before your scheduled time.
            
            Location: {self.clinic_address}
            Phone: {self.clinic_phone}
            
            Thank you for choosing {self.clinic_name}!
            """
            
            message.attach(MIMEText(plain_text, "plain"))
            message.attach(MIMEText(html_body, "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, to_email, message.as_string())
            
            logger.info(f"Confirmation email sent to {to_email} for booking #{booking_id}")
            return True, ""
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed")
            return False, "Email authentication failed. Please check configuration."
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False, f"Failed to send email: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False, f"Failed to send email: {str(e)}"
    
    def send_custom_email(
        self,
        to_email: str,
        subject: str,
        body: str
    ) -> Tuple[bool, str]:
        """
        Send a custom email (for general tool use)
        Returns: (success, error_message)
        """
        try:
            if not self.sender_email or not self.sender_password:
                return False, "Email service not configured"
            
            message = MIMEMultipart()
            message["Subject"] = subject
            message["From"] = f"{self.clinic_name} <{self.sender_email}>"
            message["To"] = to_email
            message.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, to_email, message.as_string())
            
            logger.info(f"Custom email sent to {to_email}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error sending custom email: {e}")
            return False, str(e)


# Singleton instance
_email_service: EmailService = None


def get_email_service() -> EmailService:
    """Get the email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
