import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import logging
from typing import Dict, Optional, Union, Tuple
from app.config.settings import SMTP_CONFIG

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailTemplate:
    @staticmethod
    def get_confirmation_template(appointment_data: Dict) -> Dict[str, Dict]:
        return {
            "user": {
                "subject": "Appointment Confirmation - New Turbo Education",
                "body": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="text-align: center; padding: 20px 0;">
                        <h1 style="color: #1f77b4; margin: 0;">Appointment Confirmation</h1>
                        <p style="color: #666; font-size: 16px;">New Turbo Education</p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <p style="font-size: 16px; margin-bottom: 20px;">Dear <strong>{appointment_data['name']}</strong>,</p>
                        
                        <p style="font-size: 16px; margin-bottom: 20px;">Your appointment has been successfully scheduled!</p>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #1f77b4;">
                            <h2 style="color: #1f77b4; font-size: 18px; margin: 0 0 15px 0;">📅 Appointment Details</h2>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_data['date']}</p>
                            <p style="margin: 5px 0;"><strong>Time:</strong> {appointment_data['time']}</p>
                            <p style="margin: 5px 0;"><strong>Name:</strong> {appointment_data['name']}</p>
                            <p style="margin: 5px 0;"><strong>Email:</strong> {appointment_data['email']}</p>
                            <p style="margin: 5px 0;"><strong>Phone:</strong> {appointment_data['phone']}</p>
                        </div>
                        
                        <div style="margin-top: 30px;">
                            <h3 style="color: #1f77b4; font-size: 16px;">Important Information:</h3>
                            <ul style="list-style-type: none; padding: 0;">
                                <li style="margin: 10px 0;">⏰ Please arrive 5-10 minutes before your scheduled time.</li>
                                <li style="margin: 10px 0;">📍 Location: 38-08 Union St 12A, NY 11354</li>
                                <li style="margin: 10px 0;">📱 Need to reschedule? Call us at +1 (718)-971-9914</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p style="color: #666;">We look forward to seeing you!</p>
                        <p style="color: #666; font-size: 12px;">© 2024 New Turbo Education. All rights reserved.</p>
                    </div>
                </div>
                """
            },
            "admin": {
                "subject": f"New Appointment: {appointment_data['name']}",
                "body": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                        <h2 style="color: #1f77b4; margin: 0 0 20px 0;">🎉 New Appointment Scheduled</h2>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #1f77b4;">
                            <h3 style="color: #1f77b4; font-size: 16px; margin: 0 0 15px 0;">📋 Appointment Details</h3>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_data['date']}</p>
                            <p style="margin: 5px 0;"><strong>Time:</strong> {appointment_data['time']}</p>
                            <p style="margin: 5px 0;"><strong>Name:</strong> {appointment_data['name']}</p>
                            <p style="margin: 5px 0;"><strong>Email:</strong> {appointment_data['email']}</p>
                            <p style="margin: 5px 0;"><strong>Phone:</strong> {appointment_data['phone']}</p>
                        </div>
                    </div>
                </div>
                """
            }
        }

    @staticmethod
    def get_cancellation_template(appointment_data: Dict) -> Dict[str, Dict]:
        return {
            "user": {
                "subject": "Appointment Cancellation Confirmation - New Turbo Education",
                "body": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="text-align: center; padding: 20px 0;">
                        <h1 style="color: #dc3545; margin: 0;">Appointment Cancellation</h1>
                        <p style="color: #666; font-size: 16px;">New Turbo Education</p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <p style="font-size: 16px; margin-bottom: 20px;">Dear <strong>{appointment_data['name']}</strong>,</p>
                        
                        <p style="font-size: 16px; margin-bottom: 20px;">Your appointment has been successfully cancelled.</p>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #dc3545;">
                            <h2 style="color: #dc3545; font-size: 18px; margin: 0 0 15px 0;">📅 Cancelled Appointment Details</h2>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_data['date']}</p>
                            <p style="margin: 5px 0;"><strong>Time:</strong> {appointment_data['time']}</p>
                        </div>
                        
                        <div style="margin-top: 30px;">
                            <p style="font-size: 16px;">Would you like to schedule a new appointment?</p>
                            <ul style="list-style-type: none; padding: 0;">
                                <li style="margin: 10px 0;">📱 Call us: +1 (718)-971-9914</li>
                                <li style="margin: 10px 0;">✉️ Email: newturbony@gmail.com</li>
                                <li style="margin: 10px 0;">🌐 Visit our website to book online</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p style="color: #666;">Thank you for your understanding.</p>
                        <p style="color: #666; font-size: 12px;">© 2024 New Turbo Education. All rights reserved.</p>
                    </div>
                </div>
                """
            },
            "admin": {
                "subject": f"Appointment Cancelled: {appointment_data['name']}",
                "body": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                        <h2 style="color: #dc3545; margin: 0 0 20px 0;">❌ Appointment Cancelled</h2>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #dc3545;">
                            <h3 style="color: #dc3545; font-size: 16px; margin: 0 0 15px 0;">📋 Cancelled Appointment Details</h3>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_data['date']}</p>
                            <p style="margin: 5px 0;"><strong>Time:</strong> {appointment_data['time']}</p>
                            <p style="margin: 5px 0;"><strong>Name:</strong> {appointment_data['name']}</p>
                            <p style="margin: 5px 0;"><strong>Email:</strong> {appointment_data['email']}</p>
                            <p style="margin: 5px 0;"><strong>Phone:</strong> {appointment_data['phone']}</p>
                            <p style="margin: 5px 0;"><strong>Cancelled at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        </div>
                    </div>
                </div>
                """
            }
        }

class EmailService:
    def __init__(self):
        self.config = SMTP_CONFIG
        self.validate_config()
        logger.info("Email service initialized")

    def validate_config(self) -> bool:
        """Validate email configuration"""
        missing_keys = []
        required_keys = ["server", "port", "email", "password", "admin_email"]
        
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                missing_keys.append(key)
        
        if missing_keys:
            logger.warning(f"Missing email configuration: {', '.join(missing_keys)}")
            return False
        return True

    def send_email(self, to: str, subject: str, body: str) -> Tuple[bool, Optional[str]]:
        """
        Send an email with error handling
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: HTML body of the email
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.validate_config():
            return False, "Email configuration is incomplete"
            
        logger.info(f"Sending email to: {to}")
        logger.debug(f"Subject: {subject}")
        
        msg = MIMEMultipart()
        msg["From"] = self.config["email"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(self.config["server"], self.config["port"]) as server:
                logger.debug("Connected to SMTP server")
                server.starttls()
                logger.debug("Started TLS")
                server.login(self.config["email"], self.config["password"])
                logger.debug("Logged in successfully")
                server.send_message(msg)
                logger.info("Email sent successfully")
                return True, None
        except smtplib.SMTPAuthenticationError:
            error_msg = "Failed to authenticate with email server"
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def send_appointment_notifications(self, appointment_data: Dict, template_type: str) -> Tuple[bool, Optional[str]]:
        """
        Send appointment notifications to both user and admin
        
        Args:
            appointment_data: Dictionary containing appointment details
            template_type: Type of template to use (confirmation/cancellation)
            
        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Sending {template_type} notifications for appointment: {appointment_data['email']}")
        
        templates = (EmailTemplate.get_confirmation_template(appointment_data) 
                   if template_type == "confirmation" 
                   else EmailTemplate.get_cancellation_template(appointment_data))

        # Send to user
        user_success, user_error = self.send_email(
            appointment_data["email"],
            templates["user"]["subject"],
            templates["user"]["body"]
        )
        
        if not user_success:
            logger.warning(f"Failed to send user notification: {user_error}")
        
        # Send to admin
        admin_success, admin_error = self.send_email(
            self.config["admin_email"],
            templates["admin"]["subject"],
            templates["admin"]["body"]
        )
        
        if not admin_success:
            logger.warning(f"Failed to send admin notification: {admin_error}")
        
        # Return overall success only if both emails were sent successfully
        if user_success and admin_success:
            return True, None
        elif not user_success:
            return False, f"Failed to send user notification: {user_error}"
        else:
            return False, f"Failed to send admin notification: {admin_error}" 