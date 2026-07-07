# Alert escalation system
from typing import Dict, List, Optional
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

class EscalationHandler:
    """
    Handles alert escalations to caregivers and doctors.
    
    Triggered when:
    - Missed dose persists (multiple reminders ignored)
    - Vitals are abnormal (outside safe ranges)
    - Reminders are continuously ignored (pattern detected)
    """
    
    def __init__(self):
        self.escalations: List[Dict] = []
    
    def create_escalation(
        self,
        user_id: str,
        reason: str,
        severity: str,
        context: Dict
    ) -> str:
        """
        Create an escalation alert.
        
        Args:
            user_id: User identifier
            reason: Reason for escalation (missed_dose, abnormal_vitals, reminders_ignored)
            severity: Severity level (low, medium, high, critical)
            context: Additional context (medication, vitals, etc.)
            
        Returns:
            Escalation ID
        """
        escalation_id = str(uuid.uuid4())
        
        escalation = {
            "id": escalation_id,
            "user_id": user_id,
            "reason": reason,
            "severity": severity,
            "context": context,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
            "notified_parties": []
        }
        
        self.escalations.append(escalation)
        logger.warning(f"Escalation created: {escalation_id} for user {user_id} - {reason} ({severity})")
        
        return escalation_id
    
    def escalate_to_caregiver(
        self,
        user_id: str,
        escalation_id: str,
        caregiver_id: Optional[str] = None
    ) -> bool:
        """
        Escalate alert to designated caregiver.
        
        Sends urgent notification with:
        - Patient information
        - Issue description
        - Recommended actions
        - Ability to confirm/respond
        
        Args:
            user_id: User identifier
            escalation_id: Escalation identifier
            caregiver_id: Caregiver identifier (optional)
            
        Returns:
            True if notification sent successfully
        """
        try:
            escalation = self._get_escalation(escalation_id)
            if not escalation:
                logger.error(f"Escalation not found: {escalation_id}")
                return False
            
            reason = escalation["reason"]
            severity = escalation["severity"]
            context = escalation["context"]
            
            # Build notification message
            if reason == "missed_dose":
                message = f"🚨 URGENT: Patient has missed medication {context.get('medication_name', 'unknown')}. Multiple reminders sent without response."
            elif reason == "abnormal_vitals":
                vital_type = context.get('vital_type', 'vital')
                value = context.get('value', 'N/A')
                message = f"🚨 URGENT: Patient has abnormal {vital_type}: {value}. Immediate attention recommended."
            elif reason == "reminders_ignored":
                message = f"⚠️ ALERT: Patient has ignored {context.get('reminder_count', 'multiple')} consecutive reminders for {context.get('medication_name', 'medication')}."
            else:
                message = f"⚠️ ALERT: Escalation for patient - {reason}"
            
            # In production, send via:
            # - Push notification to caregiver app
            # - SMS
            # - Phone call for critical severity
            # - Email
            
            caregiver_target = caregiver_id or "primary_caregiver"
            logger.warning(f"Escalation to caregiver {caregiver_target}: {message}")
            logger.info("[ESCALATION TO CAREGIVER] %s: %s", caregiver_target, message)
            
            # Update escalation record
            escalation["notified_parties"].append({
                "type": "caregiver",
                "id": caregiver_target,
                "notified_at": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to escalate to caregiver: {str(e)}")
            return False
    
    def escalate_to_doctor(self, user_id: str, escalation_id: str) -> bool:
        """
        Escalate alert to doctor/healthcare provider.
        
        Used for medical emergencies or when caregiver escalation is insufficient.
        
        Args:
            user_id: User identifier
            escalation_id: Escalation identifier
            
        Returns:
            True if notification sent successfully
        """
        try:
            escalation = self._get_escalation(escalation_id)
            if not escalation:
                logger.error(f"Escalation not found: {escalation_id}")
                return False
            
            reason = escalation["reason"]
            severity = escalation["severity"]
            context = escalation["context"]
            
            # Build medical alert message
            if reason == "abnormal_vitals":
                vital_type = context.get('vital_type', 'vital')
                value = context.get('value', 'N/A')
                normal_range = context.get('normal_range', 'unknown')
                message = f"🏥 MEDICAL ALERT: Patient {user_id} - Abnormal {vital_type}: {value} (normal: {normal_range}). Review required."
            elif reason == "missed_dose":
                medication = context.get('medication_name', 'medication')
                message = f"🏥 MEDICAL ALERT: Patient {user_id} - Critical medication {medication} missed. Caregiver notified but no response."
            else:
                message = f"🏥 MEDICAL ALERT: Patient {user_id} - {reason}. Severity: {severity}."
            
            # In production, send via:
            # - EHR system integration
            # - Secure messaging to doctor's portal
            # - Phone call for critical severity
            # - Pager for emergency
            
            logger.critical(f"Escalation to doctor: {message}")
            logger.info("[ESCALATION TO DOCTOR] %s", message)
            
            # Update escalation record
            escalation["notified_parties"].append({
                "type": "doctor",
                "notified_at": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to escalate to doctor: {str(e)}")
            return False
    
    def resolve_escalation(self, escalation_id: str, resolution_notes: str = "") -> bool:
        """
        Mark escalation as resolved.
        
        Args:
            escalation_id: Escalation identifier
            resolution_notes: Optional notes about resolution
            
        Returns:
            True if resolved successfully
        """
        escalation = self._get_escalation(escalation_id)
        if not escalation:
            return False
        
        escalation["status"] = "resolved"
        escalation["resolved_at"] = datetime.now().isoformat()
        escalation["resolution_notes"] = resolution_notes
        
        logger.info(f"Escalation resolved: {escalation_id}")
        return True
    
    def get_escalation_history(self, user_id: str) -> List[Dict]:
        """
        Get escalation history for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of escalations for the user
        """
        return [e for e in self.escalations if e["user_id"] == user_id]
    
    def _get_escalation(self, escalation_id: str) -> Optional[Dict]:
        """Get escalation by ID"""
        for escalation in self.escalations:
            if escalation["id"] == escalation_id:
                return escalation
        return None

# Legacy functions for backward compatibility
def create_escalation(user_id: str, alert_type: str, severity: str, message: str) -> str:
    """Legacy function - create an escalation alert"""
    handler = EscalationHandler()
    return handler.create_escalation(
        user_id=user_id,
        reason=alert_type,
        severity=severity,
        context={"message": message}
    )

def escalate_to_caregiver(user_id: str, escalation_id: str, caregiver_id: str) -> bool:
    """Legacy function - escalate alert to caregiver"""
    handler = EscalationHandler()
    return handler.escalate_to_caregiver(user_id, escalation_id, caregiver_id)

def escalate_to_doctor(user_id: str, escalation_id: str) -> bool:
    """Legacy function - escalate alert to doctor"""
    handler = EscalationHandler()
    return handler.escalate_to_doctor(user_id, escalation_id)

def get_escalation_history(user_id: str) -> List[Dict]:
    """Legacy function - get escalation history for a user"""
    handler = EscalationHandler()
    return handler.get_escalation_history(user_id)

def resolve_escalation(escalation_id: str) -> bool:
    """Legacy function - mark escalation as resolved"""
    handler = EscalationHandler()
    return handler.resolve_escalation(escalation_id)
