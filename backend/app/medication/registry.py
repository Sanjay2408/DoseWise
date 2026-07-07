# Medication registry - manages medication data
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Medication:
    """Medication data model"""
    name: str
    dosage: str
    timings: List[str]  # e.g., ["08:00", "14:00", "20:00"]
    before_after_food: str  # "before", "after", or "anytime"
    pill_image: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MedicationRegistry:
    """Manages medication registry - pure business logic"""
    
    def __init__(self):
        self._medications: Dict[str, Medication] = {}
    
    def add_medication(
        self,
        name: str,
        dosage: str,
        timings: List[str],
        before_after_food: str,
        pill_image: Optional[str] = None
    ) -> Medication:
        """
        Add a new medication to the registry
        
        Args:
            name: Medication name (unique identifier)
            dosage: Dosage information (e.g., "500mg")
            timings: List of times in HH:MM format
            before_after_food: "before", "after", or "anytime"
            pill_image: Optional image path/URL
            
        Returns:
            Created Medication object
            
        Raises:
            ValueError: If medication already exists or invalid data
        """
        if name in self._medications:
            raise ValueError(f"Medication '{name}' already exists")
        
        if not name or not dosage or not timings:
            raise ValueError("Name, dosage, and timings are required")
        
        if before_after_food not in ["before", "after", "anytime"]:
            raise ValueError("before_after_food must be 'before', 'after', or 'anytime'")
        
        # Validate timing format
        for timing in timings:
            self._validate_time_format(timing)
        
        now = datetime.now().isoformat()
        medication = Medication(
            name=name,
            dosage=dosage,
            timings=sorted(timings),  # Keep timings sorted
            before_after_food=before_after_food,
            pill_image=pill_image,
            created_at=now,
            updated_at=now
        )
        
        self._medications[name] = medication
        return medication
    
    def update_medication(
        self,
        name: str,
        dosage: Optional[str] = None,
        timings: Optional[List[str]] = None,
        before_after_food: Optional[str] = None,
        pill_image: Optional[str] = None
    ) -> Medication:
        """
        Update an existing medication
        
        Args:
            name: Medication name (identifier)
            dosage: New dosage (if provided)
            timings: New timings (if provided)
            before_after_food: New food timing (if provided)
            pill_image: New image (if provided)
            
        Returns:
            Updated Medication object
            
        Raises:
            ValueError: If medication doesn't exist or invalid data
        """
        if name not in self._medications:
            raise ValueError(f"Medication '{name}' not found")
        
        medication = self._medications[name]
        
        if dosage is not None:
            medication.dosage = dosage
        
        if timings is not None:
            for timing in timings:
                self._validate_time_format(timing)
            medication.timings = sorted(timings)
        
        if before_after_food is not None:
            if before_after_food not in ["before", "after", "anytime"]:
                raise ValueError("before_after_food must be 'before', 'after', or 'anytime'")
            medication.before_after_food = before_after_food
        
        if pill_image is not None:
            medication.pill_image = pill_image
        
        medication.updated_at = datetime.now().isoformat()
        
        return medication
    
    def get_all(self) -> List[Dict]:
        """
        Get all medications in the registry
        
        Returns:
            List of medication dictionaries
        """
        return [asdict(med) for med in self._medications.values()]
    
    def get_medication(self, name: str) -> Optional[Medication]:
        """Get a specific medication by name"""
        return self._medications.get(name)
    
    def delete_medication(self, name: str) -> bool:
        """Delete a medication from registry"""
        if name in self._medications:
            del self._medications[name]
            return True
        return False
    
    def _validate_time_format(self, time_str: str) -> None:
        """Validate time format is HH:MM"""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid time format: '{time_str}'. Expected HH:MM (24-hour format)")
