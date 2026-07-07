"""
Test script for email notification service.
Run this to verify email configuration and test all notification types.
"""
import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.notifications.email_service import get_email_service

def test_email_service():
    """Test all three email notification types."""
    print("🧪 Testing DoseWise Email Notification Service\n")
    
    email_service = get_email_service()
    
    if not email_service.enabled:
        print("❌ Email service is not enabled!")
        print("   Please check your .env file has:")
        print("   - SMTP_USERNAME")
        print("   - SMTP_PASSWORD")
        print("   - CAREGIVER_EMAIL")
        return False
    
    print(f"✅ Email service enabled")
    print(f"   SMTP Host: {email_service.smtp_host}:{email_service.smtp_port}")
    print(f"   From: {email_service.smtp_username}")
    print(f"   To: {email_service.caregiver_email}\n")
    
    # Test 1: Low Inventory Alert
    print("📧 Test 1: Sending Low Inventory Alert...")
    try:
        result = email_service.send_low_inventory_alert(
            medication_name="Aspirin (Test)",
            current_quantity=5,
            threshold=10,
            patient_name="Test Patient"
        )
        if result:
            print("   ✅ Low inventory email sent successfully!\n")
        else:
            print("   ❌ Failed to send low inventory email\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 2: Missed Dose Alert
    print("📧 Test 2: Sending Missed Dose Alert...")
    try:
        result = email_service.send_missed_dose_alert(
            medication_name="Metformin (Test)",
            scheduled_time="08:00",
            patient_name="Test Patient"
        )
        if result:
            print("   ✅ Missed dose email sent successfully!\n")
        else:
            print("   ❌ Failed to send missed dose email\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 3: Abnormal Vitals Alert
    print("📧 Test 3: Sending Abnormal Vitals Alert...")
    try:
        result = email_service.send_abnormal_vitals_alert(
            vital_type="Blood Pressure (Systolic)",
            value="180 mmHg",
            normal_range="90-160 mmHg",
            patient_name="Test Patient"
        )
        if result:
            print("   ✅ Abnormal vitals email sent successfully!\n")
        else:
            print("   ❌ Failed to send abnormal vitals email\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    print("=" * 60)
    print("✅ Email service test complete!")
    print("   Check your inbox at:", email_service.caregiver_email)
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_email_service()
