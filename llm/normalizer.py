"""
Slot normalization for ambiguous values.
Normalization is OPTIONAL and SAFE - always requires user confirmation.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from llm.groq_client import GroqClient


class SlotNormalizer:
    """
    Normalizes ambiguous slot values (dates, locations, etc.).
    ALWAYS requires user confirmation before saving.
    """
    
    def __init__(self, groq_client: Optional[GroqClient] = None):
        """Initialize normalizer."""
        self.groq_client = groq_client or GroqClient()
        self.current_date = datetime.now()
    
    def needs_normalization(self, slot_name: str, value: str) -> bool:
        """Check if a value needs normalization."""
        value_lower = value.lower().strip()
        
        # Relative date expressions
        relative_dates = [
            'tomorrow', 'today', 'yesterday',
            'next week', 'this week', 'last week',
            'next monday', 'this monday', 'last monday',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'next month', 'this month'
        ]
        
        if any(rel_date in value_lower for rel_date in relative_dates):
            return True
        
        # Ambiguous time expressions
        if 'time' in slot_name.lower():
            ambiguous_times = ['morning', 'afternoon', 'evening', 'noon', 'midnight']
            if any(amb_time in value_lower for amb_time in ambiguous_times):
                return True
        
        return False
    
    def normalize_value(self, slot_name: str, value: str, intent_name: Optional[str] = None) -> Optional[str]:
        """
        Propose normalized value.
        Returns None if normalization not needed or not possible.
        """
        if not self.needs_normalization(slot_name, value):
            return None
        
        value_lower = value.lower().strip()
        
        # Handle relative dates
        if 'date' in slot_name.lower():
            normalized = self._normalize_date(value_lower)
            if normalized:
                return normalized
        
        # Handle ambiguous times
        if 'time' in slot_name.lower():
            normalized = self._normalize_time(value_lower)
            if normalized:
                return normalized
        
        # Use Groq for complex normalization (but still require confirmation)
        try:
            prompt = f"Normalize this {slot_name} value to a specific, unambiguous format: '{value}'. Return ONLY the normalized value, nothing else. If it's a relative date like 'tomorrow' or 'next Monday', calculate the actual date based on today being {self.current_date.strftime('%Y-%m-%d, %A')}."
            
            normalized = self.groq_client.generate_response(
                prompt,
                max_tokens=50,
                temperature=0.3  # Low temperature for deterministic normalization
            )
            
            # Clean up response
            normalized = normalized.strip().strip('"').strip("'")
            return normalized if normalized and normalized != value else None
        
        except Exception as e:
            print(f"Error in normalization: {e}")
            return None
    
    def _normalize_date(self, value: str) -> Optional[str]:
        """Normalize relative date expressions."""
        value_lower = value.lower().strip()
        today = self.current_date
        weekday = today.weekday()  # 0 = Monday, 6 = Sunday
        
        # Tomorrow
        if 'tomorrow' in value_lower:
            tomorrow = today + timedelta(days=1)
            return tomorrow.strftime('%Y-%m-%d')
        
        # Today
        if 'today' in value_lower:
            return today.strftime('%Y-%m-%d')
        
        # Yesterday
        if 'yesterday' in value_lower:
            yesterday = today - timedelta(days=1)
            return yesterday.strftime('%Y-%m-%d')
        
        # Day of week
        days = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in days.items():
            if day_name in value_lower:
                # Calculate next occurrence
                days_ahead = day_num - weekday
                if days_ahead <= 0:
                    days_ahead += 7
                
                # Check for "next" modifier
                if 'next' in value_lower:
                    days_ahead += 7
                
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')
        
        return None
    
    def _normalize_time(self, value: str) -> Optional[str]:
        """Normalize ambiguous time expressions."""
        value_lower = value.lower().strip()
        
        time_mappings = {
            'morning': '09:00',
            'afternoon': '14:00',
            'evening': '18:00',
            'noon': '12:00',
            'midnight': '00:00'
        }
        
        for key, time_val in time_mappings.items():
            if key in value_lower:
                return time_val
        
        return None
    
    def generate_clarification_question(self, slot_name: str, value: str, proposed_value: str) -> str:
        """
        Generate clarification question for ambiguous values.
        Example: "Do you mean this coming Monday or next Monday?"
        """
        if 'date' in slot_name.lower() and ('monday' in value.lower() or 'tuesday' in value.lower() or 'wednesday' in value.lower() or 'thursday' in value.lower() or 'friday' in value.lower() or 'saturday' in value.lower() or 'sunday' in value.lower()):
            # For day-of-week ambiguity
            prompt = f"Generate a clarification question for this ambiguous date: '{value}'. The proposed normalized value is '{proposed_value}'. Ask if they mean this coming {value} or next {value}."
            return self.groq_client.generate_response(prompt, max_tokens=50, temperature=0.5)
        
        # Default clarification
        return f"I understood '{value}' as '{proposed_value}'. Is this correct?"

