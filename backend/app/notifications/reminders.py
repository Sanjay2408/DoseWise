# Medication reminders
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ReminderService:
    """
    Service for managing medication reminders.
    Handles initial reminders, follow-ups, and logging.
    """
    
    def __init__(self):
        self.reminder_log: List[Dict] = []
    
    def send_initial_reminder(self, user_id: str, medication: Dict) -> bool:
        """
        Send initial medication reminder to user.
        
        This is the first reminder sent at the scheduled dose time.
        
        Args:
            user_id: User identifier
            medication: Medication details (name, dosage, time, etc.)
            
        Returns:
            True if reminder sent successfully, False otherwise
        """
        try:
            medication_name = medication.get('name', 'Unknown Medication')
            dosage = medication.get('dosage', 'as prescribed')
            scheduled_time = medication.get('scheduled_time', 'now')
            
            message = f"⏰ Time to take your medication: {medication_name} ({dosage})"
            
            # In production, this would send via:
            # - Push notification
            # - SMS
            # - Email
            # - In-app notification
            
            logger.info(f"Initial reminder sent to user {user_id}: {message}")
            logger.info("[REMINDER] %s: %s", user_id, message)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send initial reminder: {str(e)}")
            return False
    
    def send_followup_reminder(self, user_id: str, medication: Dict) -> bool:
        """
        Send follow-up reminder after initial reminder was ignored or missed.
        
        Follow-ups are more urgent and may include additional context.
        
        Args:
            user_id: User identifier
            medication: Medication details
            
        Returns:
            True if follow-up sent successfully, False otherwise
        """
        try:
            medication_name = medication.get('name', 'Unknown Medication')
            dosage = medication.get('dosage', 'as prescribed')
            missed_time = medication.get('scheduled_time', 'earlier')
            
            message = f"⚠️ FOLLOW-UP: You missed {medication_name} ({dosage}) scheduled for {missed_time}. Please take it now if still safe to do so."
            
            # Follow-up reminders might be more persistent:
            # - Multiple channels
            # - Sound/vibration
            # - Cannot be easily dismissed
            
            logger.warning(f"Follow-up reminder sent to user {user_id}: {message}")
            logger.info("[FOLLOW-UP REMINDER] %s: %s", user_id, message)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send follow-up reminder: {str(e)}")
            return False
    
    def log_reminder(self, user_id: str, medication: Dict, is_followup: bool, success: bool) -> None:
        """
        Log reminder activity for audit and analysis.
        
        Args:
            user_id: User identifier
            medication: Medication details
            is_followup: Whether this was a follow-up reminder
            success: Whether reminder was sent successfully
        """
        log_entry = {
            "user_id": user_id,
            "medication_id": medication.get("id"),
            "medication_name": medication.get("name"),
            "reminder_type": "followup" if is_followup else "initial",
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "scheduled_time": medication.get("scheduled_time")
        }
        
        self.reminder_log.append(log_entry)
        logger.info(f"Reminder logged: {log_entry}")
    
    def get_reminder_history(self, user_id: str, hours: int = 24) -> List[Dict]:
        """
        Get reminder history for a user within specified hours.
        
        Args:
            user_id: User identifier
            hours: Number of hours to look back
            
        Returns:
            List of reminder log entries
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            entry for entry in self.reminder_log
            if entry["user_id"] == user_id and
            datetime.fromisoformat(entry["timestamp"]) > cutoff_time
        ]

# Legacy functions for backward compatibility
def send_reminder(user_id: str, medication: Dict) -> bool:
    """Legacy function - send medication reminder to user"""
    service = ReminderService()
    return service.send_initial_reminder(user_id, medication)

def schedule_reminder(user_id: str, medication_id: str, reminder_time: datetime) -> str:
    """Schedule a reminder for a future time"""
    # TODO: Implement reminder scheduling with task queue
    logger.info(f"Reminder scheduled for user {user_id}, medication {medication_id} at {reminder_time}")
    return f"reminder_{user_id}_{medication_id}_{int(reminder_time.timestamp())}"

def get_pending_reminders(user_id: str) -> list:
    """Get all pending reminders for a user"""
    # TODO: Implement retrieval from scheduled tasks
    return []

def dismiss_reminder(reminder_id: str) -> bool:
    """Dismiss a reminder"""
    logger.info(f"Reminder dismissed: {reminder_id}")
    return True

def snooze_reminder(reminder_id: str, minutes: int = 15) -> bool:
    """Snooze a reminder"""
    logger.info(f"Reminder snoozed for {minutes} minutes: {reminder_id}")
    return True
