# Medication reorder agent
from typing import Dict, List, Optional
from datetime import datetime
import logging
import uuid
from app.medication.inventory import get_low_stock_items
from app.reorder.pharmacy_search import PharmacySearchService

logger = logging.getLogger(__name__)

class ReorderAgent:
    """
    Autonomous agent for medication reordering.
    
    Decides when to reorder based on:
    - Current inventory levels
    - Daily usage patterns
    - Lead time for delivery
    - Safety stock thresholds
    """
    
    def __init__(self):
        self.pharmacy_search = PharmacySearchService()
        self.reorder_requests: List[Dict] = []
        self.default_threshold = 10  # days of supply
        self.safety_stock_days = 7
    
    def decide_reorder(self, user_id: str, medication: Dict, current_quantity: int) -> Dict:
        """
        Decide whether to reorder medication.
        
        Logic:
        1. Calculate days of supply remaining
        2. Check against threshold
        3. Consider historical usage patterns
        4. Suggest reorder quantity
        
        Args:
            user_id: User identifier
            medication: Medication details
            current_quantity: Current quantity in stock
            
        Returns:
            Decision dict with should_reorder and suggested_quantity
        """
        daily_dosage = medication.get('daily_dosage', 1)
        threshold = medication.get('reorder_threshold', self.default_threshold)
        
        # Calculate days of supply remaining
        if daily_dosage > 0:
            days_remaining = current_quantity / daily_dosage
        else:
            days_remaining = current_quantity  # Assume 1 per day if not specified
        
        should_reorder = days_remaining <= threshold
        
        # Calculate suggested reorder quantity
        # Target: 30 days supply + safety stock
        target_days = 30
        suggested_quantity = 0
        
        if should_reorder:
            suggested_quantity = int((target_days + self.safety_stock_days) * daily_dosage)
        
        decision = {
            "should_reorder": should_reorder,
            "days_remaining": round(days_remaining, 1),
            "threshold": threshold,
            "suggested_quantity": suggested_quantity,
            "reason": self._generate_reorder_reason(days_remaining, threshold)
        }
        
        logger.info(f"Reorder decision for {medication.get('name')}: {decision}")
        return decision
    
    def create_reorder_request(self, user_id: str, medication: Dict, quantity: int) -> Dict:
        """
        Create a reorder request (no payment processing).
        
        Output includes:
        - Medication details
        - Quantity to reorder
        - Pharmacy options (from pharmacy search)
        - Estimated timeline
        
        Args:
            user_id: User identifier
            medication: Medication details
            quantity: Quantity to reorder
            
        Returns:
            Reorder request details
        """
        reorder_id = str(uuid.uuid4())
        
        # Search for pharmacy options
        pharmacy_options = self.pharmacy_search.search_pharmacies(
            medication_name=medication.get('name'),
            quantity=quantity
        )
        
        reorder_request = {
            "reorder_id": reorder_id,
            "user_id": user_id,
            "medication": {
                "id": medication.get('id'),
                "name": medication.get('name'),
                "dosage": medication.get('dosage'),
                "form": medication.get('form', 'tablet')
            },
            "quantity": quantity,
            "pharmacy_options": pharmacy_options,
            "status": "pending_user_approval",
            "created_at": datetime.now().isoformat(),
            "estimated_delivery": "3-5 business days"
        }
        
        self.reorder_requests.append(reorder_request)
        
        logger.info(f"Reorder request created: {reorder_id} for {medication.get('name')} x{quantity}")
        logger.info("[REORDER REQUEST] %s: %s x%s", reorder_id, medication.get("name"), quantity)
        logger.info("  Pharmacy options: %s available", len(pharmacy_options))
        
        return reorder_request
    
    def get_reorder_status(self, reorder_id: str) -> Optional[Dict]:
        """Get status of a reorder request"""
        for request in self.reorder_requests:
            if request["reorder_id"] == reorder_id:
                return request
        return None
    
    def _generate_reorder_reason(self, days_remaining: float, threshold: int) -> str:
        """Generate human-readable reason for reorder decision"""
        if days_remaining <= 0:
            return "Medication out of stock"
        elif days_remaining <= 3:
            return f"Critical: Only {days_remaining:.1f} days remaining"
        elif days_remaining <= threshold:
            return f"Low stock: {days_remaining:.1f} days remaining (threshold: {threshold} days)"
        else:
            return f"Sufficient stock: {days_remaining:.1f} days remaining"

# Legacy functions for backward compatibility
def check_inventory(user_id: str) -> Dict:
    """Legacy function - check inventory and determine reorder needs"""
    low_stock = get_low_stock_items(user_id)
    
    return {
        "user_id": user_id,
        "low_stock_items": low_stock,
        "reorder_needed": len(low_stock) > 0
    }

def create_reorder(user_id: str, medication_id: str, quantity: int) -> bool:
    """Legacy function - create a reorder request"""
    agent = ReorderAgent()
    medication = {"id": medication_id, "name": "Medication"}
    request = agent.create_reorder_request(user_id, medication, quantity)
    return request is not None

def find_best_pharmacy(user_id: str, medications: List[str]) -> Optional[Dict]:
    """Legacy function - find the best pharmacy for reordering"""
    search = PharmacySearchService()
    options = search.search_pharmacies(medication_name=medications[0] if medications else "")
    return options[0] if options else None

def estimate_reorder_cost(medications: List[str]) -> float:
    """Legacy function - estimate cost for reorder"""
    # Mock estimation: $10-50 per medication
    return len(medications) * 25.0
