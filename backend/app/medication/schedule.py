# Medication scheduling - manages medication schedules
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class DoseSchedule:
    """Represents a scheduled dose"""
    med_name: str
    scheduled_time: str  # HH:MM format
    taken: bool = False
    taken_at: Optional[str] = None  # ISO timestamp when taken


@dataclass
class DoseRecord:
    """Represents a dose that's due or missed"""
    med_name: str
    scheduled_time: str
    status: str  # "due", "missed", "taken"
    scheduled_datetime: str  # ISO timestamp
    taken_at: Optional[str] = None


class ScheduleManager:
    """Manages medication schedules - pure business logic"""
    
    def __init__(self):
        # Structure: {date_str: {med_name: [DoseSchedule, ...]}}
        self._schedules: Dict[str, Dict[str, List[DoseSchedule]]] = {}
        self._dose_history: List[Dict] = []  # History of all taken doses
    
    def add_medication_schedule(
        self,
        med_name: str,
        timings: List[str],
        start_date: Optional[datetime] = None
    ) -> None:
        """
        Add a medication to the schedule
        
        Args:
            med_name: Name of the medication
            timings: List of times in HH:MM format
            start_date: When to start scheduling (default: today)
        """
        if start_date is None:
            start_date = datetime.now()
        
        date_key = start_date.strftime("%Y-%m-%d")
        
        if date_key not in self._schedules:
            self._schedules[date_key] = {}
        
        if med_name not in self._schedules[date_key]:
            self._schedules[date_key][med_name] = []
        
        for timing in timings:
            dose = DoseSchedule(med_name=med_name, scheduled_time=timing)
            self._schedules[date_key][med_name].append(dose)
    
    def get_due_doses(self, current_time: datetime) -> List[Dict]:
        """
        Get doses that are due now (within a time window)
        
        Args:
            current_time: Current datetime
            
        Returns:
            List of due dose dictionaries
        """
        due_window_minutes = 30  # Doses are "due" 30 min before and after scheduled time
        date_key = current_time.strftime("%Y-%m-%d")
        
        if date_key not in self._schedules:
            return []
        
        due_doses = []
        current_time_minutes = current_time.hour * 60 + current_time.minute
        
        for med_name, doses in self._schedules[date_key].items():
            for dose in doses:
                if dose.taken:
                    continue
                
                # Parse scheduled time
                hour, minute = map(int, dose.scheduled_time.split(":"))
                scheduled_minutes = hour * 60 + minute
                
                # Check if within due window
                time_diff = abs(current_time_minutes - scheduled_minutes)
                
                if time_diff <= due_window_minutes:
                    scheduled_dt = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    due_doses.append(DoseRecord(
                        med_name=med_name,
                        scheduled_time=dose.scheduled_time,
                        status="due",
                        scheduled_datetime=scheduled_dt.isoformat()
                    ))
        
        return [asdict(dose) for dose in due_doses]
    
    def get_missed_doses(self, current_time: datetime) -> List[Dict]:
        """
        Get doses that were missed (scheduled time passed, not taken)
        
        Args:
            current_time: Current datetime
            
        Returns:
            List of missed dose dictionaries
        """
        date_key = current_time.strftime("%Y-%m-%d")
        
        if date_key not in self._schedules:
            return []
        
        missed_doses = []
        current_time_minutes = current_time.hour * 60 + current_time.minute
        missed_threshold_minutes = 60  # Consider missed after 1 hour
        
        for med_name, doses in self._schedules[date_key].items():
            for dose in doses:
                if dose.taken:
                    continue
                
                # Parse scheduled time
                hour, minute = map(int, dose.scheduled_time.split(":"))
                scheduled_minutes = hour * 60 + minute
                
                # Check if past scheduled time by threshold
                time_diff = current_time_minutes - scheduled_minutes
                
                if time_diff > missed_threshold_minutes:
                    scheduled_dt = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    missed_doses.append(DoseRecord(
                        med_name=med_name,
                        scheduled_time=dose.scheduled_time,
                        status="missed",
                        scheduled_datetime=scheduled_dt.isoformat()
                    ))
        
        return [asdict(dose) for dose in missed_doses]
    
    def mark_dose_taken(
        self,
        med_name: str,
        time: str,
        taken_at: Optional[datetime] = None
    ) -> bool:
        """
        Mark a dose as taken
        
        Args:
            med_name: Name of the medication
            time: Scheduled time in HH:MM format
            taken_at: When it was taken (default: now)
            
        Returns:
            True if dose was found and marked, False otherwise
        """
        if taken_at is None:
            taken_at = datetime.now()
        
        date_key = taken_at.strftime("%Y-%m-%d")
        
        if date_key not in self._schedules:
            return False
        
        if med_name not in self._schedules[date_key]:
            return False
        
        # Find the dose and mark it taken
        for dose in self._schedules[date_key][med_name]:
            if dose.scheduled_time == time and not dose.taken:
                dose.taken = True
                dose.taken_at = taken_at.isoformat()
                
                # Add to history
                self._dose_history.append({
                    "med_name": med_name,
                    "scheduled_time": time,
                    "taken_at": dose.taken_at,
                    "date": date_key
                })
                
                return True
        
        return False
    
    def get_schedule_for_date(self, date: datetime) -> Dict[str, List[Dict]]:
        """Get all scheduled doses for a specific date"""
        date_key = date.strftime("%Y-%m-%d")
        
        if date_key not in self._schedules:
            return {}
        
        result = {}
        for med_name, doses in self._schedules[date_key].items():
            result[med_name] = [asdict(dose) for dose in doses]
        
        return result
    
    def get_adherence_rate(self, med_name: Optional[str] = None, days: int = 7) -> float:
        """
        Calculate medication adherence rate
        
        Args:
            med_name: Specific medication (None for all)
            days: Number of days to look back
            
        Returns:
            Adherence rate as percentage (0-100)
        """
        if not self._dose_history:
            return 0.0
        
        # Filter history
        relevant_doses = self._dose_history
        if med_name:
            relevant_doses = [d for d in relevant_doses if d["med_name"] == med_name]
        
        if not relevant_doses:
            return 0.0
        
        # Calculate total scheduled vs taken (simplified)
        taken_count = len(relevant_doses)
        
        # For accurate calculation, we'd need to count total scheduled doses
        # This is a simplified version
        return 100.0 if taken_count > 0 else 0.0
