# Pharmacy search and integration
from typing import List, Dict, Optional
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class PharmacySearchService:
    """
    Service for searching pharmacies and getting medication prices.
    
    Uses REAL Indian pharmacy websites with search functionality.
    Does NOT auto-order medicines (compliance & safety).
    
    Returns pharmacy search data:
    - name: Pharmacy name
    - price: Estimated price (mock data)
    - link: Working search URL to real pharmacy website
    - action_type: "external_search" (agent safety design)
    """
    
    def __init__(self):
        # Real Indian online pharmacies with working search endpoints
        self.pharmacies = [
            {
                "id": "pharmacy_001",
                "name": "Tata 1mg",
                "base_url": "https://www.1mg.com/search/all",
                "rating": 4.8,
                "delivery_time": "1-2 days"
            },
            {
                "id": "pharmacy_002",
                "name": "PharmEasy",
                "base_url": "https://pharmeasy.in/search/all",
                "rating": 4.7,
                "delivery_time": "1-3 days"
            },
            {
                "id": "pharmacy_003",
                "name": "NetMeds",
                "base_url": "https://www.netmeds.com/catalogsearch/result",
                "rating": 4.6,
                "delivery_time": "2-4 days"
            },
            {
                "id": "pharmacy_004",
                "name": "Apollo Pharmacy",
                "base_url": "https://www.apollopharmacy.in/search-medicines",
                "rating": 4.5,
                "delivery_time": "Same day / 1 day"
            }
        ]
    
    def search_pharmacies(
        self,
        medication_name: str,
        quantity: int = 30,
        user_location: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for pharmacies that have the required medication.
        
        Returns working search links to REAL pharmacy websites.
        Does NOT auto-order (proper agent safety design).
        
        Returns data with:
        - name: Pharmacy name
        - price: Estimated price (mock calculation)
        - link: Working search URL to real pharmacy website
        - action_type: "external_search" (agent reasoning)
        - availability: In stock status (mock)
        - delivery_time: Estimated delivery time
        
        Args:
            medication_name: Name of the medication
            quantity: Quantity needed
            user_location: Optional user location for proximity search
            
        Returns:
            List of pharmacy search options with working links
        """
        results = []
        
        # Mock price generation based on pharmacy
        base_price = self._estimate_medication_price(medication_name, quantity)
        
        for pharmacy in self.pharmacies:
            # Each pharmacy has slightly different pricing (mock data)
            price_variation = pharmacy["rating"] / 4.5  # Higher rated = slightly higher price
            price = round(base_price * price_variation, 2)
            
            # Build WORKING search link using proper URL encoding
            query = urlencode({"q": medication_name})
            link = f"{pharmacy['base_url']}?{query}"
            
            pharmacy_option = {
                "name": pharmacy["name"],
                "price": price,
                "link": link,
                "action_type": "external_search",  # Agent safety: no auto-purchase
                "availability": "Search required",  # Honest about not knowing real stock
                "delivery_time": pharmacy["delivery_time"],
                "rating": pharmacy["rating"],
                "pharmacy_id": pharmacy["id"]
            }
            
            results.append(pharmacy_option)
        
        # Sort by price (lowest first, based on mock estimation)
        results.sort(key=lambda x: x["price"])
        
        logger.info(f"Found {len(results)} pharmacy search options for {medication_name}")
        return results
    
    def get_pharmacy_details(self, pharmacy_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific pharmacy.
        
        Args:
            pharmacy_id: Pharmacy identifier
            
        Returns:
            Pharmacy details or None if not found
        """
        for pharmacy in self.pharmacies:
            if pharmacy["id"] == pharmacy_id:
                return pharmacy
        return None
    
    def _estimate_medication_price(self, medication_name: str, quantity: int) -> float:
        """
        Estimate base price for medication.
        
        Mock pricing logic:
        - Common medications: $10-30
        - Specialized medications: $30-100
        - Quantity adjustments
        
        Args:
            medication_name: Name of the medication
            quantity: Quantity needed
            
        Returns:
            Estimated base price
        """
        # Simple mock pricing
        common_meds = ['aspirin', 'ibuprofen', 'acetaminophen', 'vitamins']
        
        medication_lower = medication_name.lower()
        
        if any(common in medication_lower for common in common_meds):
            base_per_unit = 0.50
        else:
            base_per_unit = 1.50
        
        # Bulk discount for larger quantities
        if quantity >= 90:
            discount_factor = 0.85
        elif quantity >= 60:
            discount_factor = 0.90
        else:
            discount_factor = 1.0
        
        total_price = base_per_unit * quantity * discount_factor
        return round(total_price, 2)

# Legacy functions for backward compatibility
def search_pharmacies(user_location: str, medications: List[str]) -> List[Dict]:
    """Legacy function - search for pharmacies that have the required medications"""
    service = PharmacySearchService()
    if not medications:
        return []
    return service.search_pharmacies(
        medication_name=medications[0],
        user_location=user_location
    )

def get_pharmacy_prices(pharmacy_id: str, medications: List[str]) -> Dict:
    """Legacy function - get prices from a specific pharmacy"""
    service = PharmacySearchService()
    pharmacy = service.get_pharmacy_details(pharmacy_id)
    
    if not pharmacy or not medications:
        return {}
    
    # Return mock prices for each medication
    prices = {}
    for med in medications:
        base_price = service._estimate_medication_price(med, 30)
        prices[med] = round(base_price, 2)
    
    return prices

def check_pharmacy_availability(pharmacy_id: str, medication_id: str) -> bool:
    """Legacy function - check if a pharmacy has a medication in stock"""
    service = PharmacySearchService()
    pharmacy = service.get_pharmacy_details(pharmacy_id)
    # Mock: all pharmacies have all medications in stock
    return pharmacy is not None

def submit_prescription(pharmacy_id: str, prescription: Dict) -> str:
    """Legacy function - submit a prescription to a pharmacy"""
    import uuid
    order_id = str(uuid.uuid4())
    logger.info(f"Prescription submitted to pharmacy {pharmacy_id}: {order_id}")
    return order_id
