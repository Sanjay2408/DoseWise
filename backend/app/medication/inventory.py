# Medication inventory - tracks medication stock levels
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class InventoryItem:
    """Represents inventory for a medication"""
    med_name: str
    quantity: int
    low_stock_threshold: int = 10
    last_updated: Optional[str] = None
    last_refilled: Optional[str] = None


class InventoryManager:
    """Manages medication inventory - pure business logic"""
    
    def __init__(self, default_low_stock_threshold: int = 10):
        self._inventory: Dict[str, InventoryItem] = {}
        self._default_threshold = default_low_stock_threshold
        self._transaction_log: List[Dict] = []
    
    def add_medication(
        self,
        med_name: str,
        initial_quantity: int = 0,
        low_stock_threshold: Optional[int] = None
    ) -> InventoryItem:
        """
        Add a medication to inventory
        
        Args:
            med_name: Name of the medication
            initial_quantity: Starting quantity
            low_stock_threshold: Custom threshold (uses default if None)
            
        Returns:
            Created InventoryItem
            
        Raises:
            ValueError: If medication already exists
        """
        if med_name in self._inventory:
            raise ValueError(f"Medication '{med_name}' already in inventory")
        
        if initial_quantity < 0:
            raise ValueError("Initial quantity cannot be negative")
        
        threshold = low_stock_threshold if low_stock_threshold is not None else self._default_threshold
        now = datetime.now().isoformat()
        
        item = InventoryItem(
            med_name=med_name,
            quantity=initial_quantity,
            low_stock_threshold=threshold,
            last_updated=now,
            last_refilled=now if initial_quantity > 0 else None
        )
        
        self._inventory[med_name] = item
        
        self._log_transaction(med_name, "add", 0, initial_quantity, "Initial stock")
        
        return item
    
    def decrement(self, med_name: str, amount: int = 1) -> int:
        """
        Decrement medication quantity (e.g., after dose taken)
        
        Args:
            med_name: Name of the medication
            amount: Amount to decrement (default: 1)
            
        Returns:
            New quantity after decrement
            
        Raises:
            ValueError: If medication not found or insufficient quantity
        """
        if med_name not in self._inventory:
            raise ValueError(f"Medication '{med_name}' not found in inventory")
        
        if amount <= 0:
            raise ValueError("Decrement amount must be positive")
        
        item = self._inventory[med_name]
        
        if item.quantity < amount:
            raise ValueError(
                f"Insufficient quantity for '{med_name}'. "
                f"Available: {item.quantity}, Requested: {amount}"
            )
        
        old_quantity = item.quantity
        item.quantity -= amount
        item.last_updated = datetime.now().isoformat()
        
        self._log_transaction(med_name, "decrement", old_quantity, item.quantity, f"Dose taken (-{amount})")
        
        # Send email alert if inventory is now low
        if item.quantity <= item.low_stock_threshold and old_quantity > item.low_stock_threshold:
            try:
                from app.notifications.email_service import get_email_service
                email_service = get_email_service()
                email_service.send_low_inventory_alert(
                    medication_name=med_name,
                    current_quantity=item.quantity,
                    threshold=item.low_stock_threshold
                )
            except Exception as e:
                # Don't fail the operation if email fails
                import logging
                logging.getLogger(__name__).warning(f"Failed to send low inventory email: {e}")
        
        return item.quantity
    
    def increment(self, med_name: str, amount: int) -> int:
        """
        Increment medication quantity (e.g., after refill)
        
        Args:
            med_name: Name of the medication
            amount: Amount to add
            
        Returns:
            New quantity after increment
            
        Raises:
            ValueError: If medication not found or invalid amount
        """
        if med_name not in self._inventory:
            raise ValueError(f"Medication '{med_name}' not found in inventory")
        
        if amount <= 0:
            raise ValueError("Increment amount must be positive")
        
        item = self._inventory[med_name]
        old_quantity = item.quantity
        
        item.quantity += amount
        now = datetime.now().isoformat()
        item.last_updated = now
        item.last_refilled = now
        
        self._log_transaction(med_name, "increment", old_quantity, item.quantity, f"Refilled (+{amount})")
        
        return item.quantity
    
    def is_low_stock(self, med_name: str) -> bool:
        """
        Check if medication is at or below low stock threshold
        
        Args:
            med_name: Name of the medication
            
        Returns:
            True if low stock, False otherwise
            
        Raises:
            ValueError: If medication not found
        """
        if med_name not in self._inventory:
            raise ValueError(f"Medication '{med_name}' not found in inventory")
        
        item = self._inventory[med_name]
        return item.quantity <= item.low_stock_threshold
    
    def get_inventory_status(self) -> List[Dict]:
        """
        Get complete inventory status for all medications
        
        Returns:
            List of inventory items with status information
        """
        status = []
        
        for item in self._inventory.values():
            item_dict = asdict(item)
            item_dict["is_low_stock"] = item.quantity <= item.low_stock_threshold
            item_dict["status"] = self._get_status_label(item)
            status.append(item_dict)
        
        return status
    
    def get_item(self, med_name: str) -> Optional[Dict]:
        """Get inventory details for a specific medication"""
        if med_name not in self._inventory:
            return None
        
        item = self._inventory[med_name]
        item_dict = asdict(item)
        item_dict["is_low_stock"] = item.quantity <= item.low_stock_threshold
        item_dict["status"] = self._get_status_label(item)
        
        return item_dict
    
    def set_low_stock_threshold(self, med_name: str, threshold: int) -> None:
        """Update the low stock threshold for a medication"""
        if med_name not in self._inventory:
            raise ValueError(f"Medication '{med_name}' not found in inventory")
        
        if threshold < 0:
            raise ValueError("Threshold cannot be negative")
        
        self._inventory[med_name].low_stock_threshold = threshold
        self._inventory[med_name].last_updated = datetime.now().isoformat()

    def set_quantity(self, med_name: str, quantity: int) -> int:
        """
        Set absolute quantity for a medication (e.g. from setup/edit).
        
        Args:
            med_name: Name of the medication
            quantity: New quantity
            
        Returns:
            New quantity
        """
        if med_name not in self._inventory:
            raise ValueError(f"Medication '{med_name}' not found in inventory")
        
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
            
        item = self._inventory[med_name]
        old_quantity = item.quantity
        item.quantity = quantity
        item.last_updated = datetime.now().isoformat()
        
        if quantity > old_quantity:
            item.last_refilled = datetime.now().isoformat()
            
        self._log_transaction(med_name, "set", old_quantity, quantity, "Manual update/Setup")
        return quantity
    
    def estimate_days_remaining(self, med_name: str, daily_consumption: int) -> Optional[int]:
        """
        Estimate days until stock runs out
        
        Args:
            med_name: Name of the medication
            daily_consumption: Pills consumed per day
            
        Returns:
            Estimated days remaining, or None if insufficient data
        """
        if med_name not in self._inventory:
            return None
        
        if daily_consumption <= 0:
            return None
        
        item = self._inventory[med_name]
        
        if item.quantity == 0:
            return 0
        
        return item.quantity // daily_consumption
    
    def get_low_stock_medications(self) -> List[Dict]:
        """Get all medications that are currently low in stock"""
        return [
            item for item in self.get_inventory_status()
            if item["is_low_stock"]
        ]
    
    def _get_status_label(self, item: InventoryItem) -> str:
        """Get human-readable status label"""
        if item.quantity == 0:
            return "out_of_stock"
        elif item.quantity <= item.low_stock_threshold:
            return "low_stock"
        elif item.quantity <= item.low_stock_threshold * 2:
            return "adequate"
        else:
            return "well_stocked"
    
    def _log_transaction(
        self,
        med_name: str,
        action: str,
        old_quantity: int,
        new_quantity: int,
        note: str
    ) -> None:
        """Log inventory transaction for audit trail"""
        self._transaction_log.append({
            "timestamp": datetime.now().isoformat(),
            "med_name": med_name,
            "action": action,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "note": note
        })
    
    def get_transaction_history(self, med_name: Optional[str] = None) -> List[Dict]:
        """Get transaction history, optionally filtered by medication"""
        if med_name:
            return [t for t in self._transaction_log if t["med_name"] == med_name]
        return self._transaction_log.copy()


def get_low_stock_items(user_id: str) -> List[Dict]:
    """
    Return low-stock items for the given user.
    Used by reorder_agent for legacy check_inventory().
    Inventory is managed per-request from AgentState; callers that have
    state.inventory should use InventoryManager with that data and
    get_low_stock_medications() instead. This returns [] when no
    inventory context is available.
    """
    return []
