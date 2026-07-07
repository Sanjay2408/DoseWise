"""
Email notification service for DoseWise.
Sends alerts to caregivers for low inventory, missed doses, and abnormal vitals.
Uses SMTP with configurable credentials from environment variables.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    """SMTP-based email notification service."""
    
    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.caregiver_email = os.environ.get("CAREGIVER_EMAIL", "")
        self.enabled = bool(self.smtp_username and self.smtp_password and self.caregiver_email)
        
        if not self.enabled:
            logger.info("Email service disabled - SMTP credentials not configured")
    
    def send_email(self, subject: str, html_body: str, to_email: Optional[str] = None) -> bool:
        """
        Send an email notification.
        
        Args:
            subject: Email subject line
            html_body: HTML content of the email
            to_email: Recipient email (defaults to CAREGIVER_EMAIL)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email not sent - service disabled")
            return False
        
        recipient = to_email or self.caregiver_email
        if not recipient:
            logger.warning("Email not sent - no recipient configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_username
            msg['To'] = recipient
            
            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipient}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_low_inventory_alert(self, medication_name: str, current_quantity: int, threshold: int, patient_name: str = "Patient") -> bool:
        """Send alert when medication inventory is low."""
        subject = f"⚠️ Low Inventory Alert - {medication_name}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ef4444; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
                .alert-box {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 15px 0; }}
                .details {{ background: white; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .footer {{ color: #6b7280; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
                .btn {{ background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🏥 DoseWise - Low Inventory Alert</h2>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <strong>⚠️ Action Required</strong>
                        <p>Medication inventory has fallen below the safe threshold.</p>
                    </div>
                    
                    <div class="details">
                        <h3>Alert Details</h3>
                        <p><strong>Patient:</strong> {patient_name}</p>
                        <p><strong>Medication:</strong> {medication_name}</p>
                        <p><strong>Current Quantity:</strong> {current_quantity} pills</p>
                        <p><strong>Threshold:</strong> {threshold} pills</p>
                        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</p>
                    </div>
                    
                    <h3>Recommended Actions</h3>
                    <ul>
                        <li>Order refill immediately to avoid running out</li>
                        <li>Check prescription validity</li>
                        <li>Contact pharmacy or use the "Buy Now" feature in DoseWise</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from DoseWise medication management system.</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(subject, html_body)
    
    def send_missed_dose_alert(self, medication_name: str, scheduled_time: str, patient_name: str = "Patient") -> bool:
        """Send alert when a scheduled dose is missed."""
        subject = f"⏰ Missed Dose Alert - {medication_name}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f59e0b; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
                .alert-box {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 15px 0; }}
                .details {{ background: white; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .footer {{ color: #6b7280; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🏥 DoseWise - Missed Dose Alert</h2>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <strong>⏰ Attention Required</strong>
                        <p>A scheduled medication dose has been missed.</p>
                    </div>
                    
                    <div class="details">
                        <h3>Alert Details</h3>
                        <p><strong>Patient:</strong> {patient_name}</p>
                        <p><strong>Medication:</strong> {medication_name}</p>
                        <p><strong>Scheduled Time:</strong> {scheduled_time}</p>
                        <p><strong>Alert Time:</strong> {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</p>
                    </div>
                    
                    <h3>Recommended Actions</h3>
                    <ul>
                        <li>Check on the patient immediately</li>
                        <li>Ensure the medication is taken as soon as possible</li>
                        <li>Review medication schedule and set reminders</li>
                        <li>Contact healthcare provider if doses are frequently missed</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from DoseWise medication management system.</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(subject, html_body)
    
    def send_abnormal_vitals_alert(self, vital_type: str, value: Any, normal_range: str, patient_name: str = "Patient") -> bool:
        """Send alert when vitals are outside normal range."""
        subject = f"🚨 Abnormal Vitals Alert - {vital_type}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #dc2626; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
                .alert-box {{ background: #fee2e2; border-left: 4px solid #dc2626; padding: 15px; margin: 15px 0; }}
                .details {{ background: white; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .footer {{ color: #6b7280; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
                .urgent {{ color: #dc2626; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🏥 DoseWise - Abnormal Vitals Alert</h2>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <strong class="urgent">🚨 URGENT - Immediate Attention Required</strong>
                        <p>Patient vitals are outside the normal range.</p>
                    </div>
                    
                    <div class="details">
                        <h3>Alert Details</h3>
                        <p><strong>Patient:</strong> {patient_name}</p>
                        <p><strong>Vital Sign:</strong> {vital_type}</p>
                        <p><strong>Recorded Value:</strong> <span class="urgent">{value}</span></p>
                        <p><strong>Normal Range:</strong> {normal_range}</p>
                        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</p>
                    </div>
                    
                    <h3>Recommended Actions</h3>
                    <ul>
                        <li><strong>Check on the patient immediately</strong></li>
                        <li>Verify the reading and retest if possible</li>
                        <li>Contact healthcare provider or emergency services if needed</li>
                        <li>Monitor patient closely and record any symptoms</li>
                        <li>Review recent medications and activities</li>
                    </ul>
                    
                    <p style="color: #dc2626; font-weight: bold; margin-top: 20px;">
                        ⚠️ If this is a medical emergency, call emergency services immediately.
                    </p>
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from DoseWise medication management system.</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(subject, html_body)


# Global instance
_email_service = None

def get_email_service() -> EmailService:
    """Get or create the global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
