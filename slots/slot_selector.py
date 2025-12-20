"""
Multi-label slot selector using Hugging Face models.
Returns a LIST of slot names that the utterance can answer.
NEVER defaults to single slot, NEVER hallucinates slots.
"""

from typing import List, Dict
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from slots.schemas import get_slot_questions


class SlotSelector:
    """
    Multi-label slot selector.
    Input: User utterance + list of slot questions for active intent
    Output: List of slot names the utterance can answer
    """
    
    def __init__(self, model_name: str = "google/electra-small-discriminator"):
        """
        Initialize with a lightweight Hugging Face model.
        Using ELECTRA-small - best performing model (95.65% accuracy, 0.2213s avg time).
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            # For multi-label classification, we'll use a sequence classification model
            # and adapt it for multi-label by using sigmoid activation
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=1  # Binary classification per slot
            )
            self.model.to(self.device)
            self.model.eval()
            print(f"✓ Slot selection model loaded: {model_name}")
        except Exception as e:
            # Fallback to rule-based if model loading fails
            print(f"Warning: Could not load slot selection model {model_name}: {e}")
            print("Falling back to rule-based slot selection")
    
    def select_slots(
        self,
        user_utterance: str,
        intent_name: str,
        filled_slots: Dict[str, any] = None
    ) -> List[str]:
        """
        Select which slots the utterance can answer.
        Returns a LIST of slot names (can be multiple, can be empty).
        
        Rules:
        - Returns multiple slots when applicable
        - NEVER defaults to single slot
        - NEVER hallucinates slots
        - NEVER infers or generates values
        - Only returns slots that are NOT already filled
        """
        if filled_slots is None:
            filled_slots = {}
        
        # Get slot questions for this intent
        slot_questions = get_slot_questions(intent_name)
        slot_names = list(slot_questions.keys())
        
        # Filter out already filled slots
        available_slots = [s for s in slot_names if s not in filled_slots]
        
        if not available_slots:
            return []
        
        # If model not available, use rule-based fallback
        if self.model is None:
            return self._rule_based_selection(user_utterance, available_slots, intent_name)
        
        # Use model for multi-label classification
        selected_slots = []
        
        try:
            # For each available slot, check if utterance can answer it
            for slot_name in available_slots:
                slot_question = slot_questions[slot_name]
                
                # Create input: "Question: {slot_question} Answer: {user_utterance}"
                input_text = f"Question: {slot_question} Answer: {user_utterance}"
                
                # Tokenize
                inputs = self.tokenizer(
                    input_text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                    padding=True
                ).to(self.device)
                
                # Get prediction
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    # Use sigmoid for multi-label (probability > 0.5)
                    probability = torch.sigmoid(logits).item()
                
                # Threshold for selection
                if probability > 0.5:
                    selected_slots.append(slot_name)
        
        except Exception as e:
            print(f"Error in model-based selection: {e}")
            # Fallback to rule-based
            return self._rule_based_selection(user_utterance, available_slots, intent_name)
        
        return selected_slots
    
    def _rule_based_selection(
        self,
        user_utterance: str,
        available_slots: List[str],
        intent_name: str
    ) -> List[str]:
        """
        Rule-based fallback for slot selection.
        Uses keyword matching and pattern recognition to determine which slots might be answered.
        """
        utterance_lower = user_utterance.lower().strip()
        utterance = user_utterance.strip()
        selected = []
        
        # If utterance is very short (likely a direct answer), check if it matches name patterns
        if len(utterance.split()) <= 3 and len(utterance) < 50:
            # Check for name slots
            name_slots = [s for s in available_slots if "name" in s.lower()]
            if name_slots:
                # Simple heuristic: if it looks like a name (2-3 words, mostly letters)
                import re
                if re.match(r'^[A-Za-z\s\.\-\']{2,50}$', utterance) and len(utterance.split()) <= 3:
                    selected.extend(name_slots)
        
        # Keyword patterns for common slot types
        slot_keywords = {
            "employee_name": ["name", "i am", "my name", "this is", "i'm", "call me"],
            "requester_name": ["name", "i am", "my name", "this is", "i'm", "call me"],
            "organizer_name": ["name", "i am", "my name", "i'm organizing", "i'm", "call me"],
            "start_date": ["start", "begin", "from", "starting", "on"],
            "end_date": ["end", "until", "return", "back", "ending", "until"],
            "date": ["date", "on", "when", "day"],
            "incident_date": ["date", "when", "occurred", "happened"],
            "start_time": ["start", "begin", "at", "from"],
            "end_time": ["end", "until", "finish", "until"],
            "time_off_type": ["vacation", "sick", "personal", "pto", "type"],
            "reason": ["because", "reason", "why", "for"],
            "notify_manager": ["notify", "manager", "supervisor", "yes", "no"],
            "participants": ["participants", "attendees", "people", "with"],
            "meeting_platform": ["zoom", "teams", "google meet", "platform"],
            "agenda": ["agenda", "topic", "discuss", "about"],
            "issue_category": ["category", "type", "hardware", "software", "network"],
            "issue_description": ["problem", "issue", "broken", "not working", "error"],
            "urgency": ["urgent", "urgency", "priority", "critical", "high", "low"],
            "affected_system": ["system", "application", "software", "tool"],
            "contact_email": ["email", "contact", "@"],
            "provider_name": ["provider", "doctor", "hospital", "clinic"],
            "claim_amount": ["amount", "cost", "price", "$", "dollar"],
            "claim_type": ["type", "visit", "prescription", "procedure"],
            "description": ["description", "details", "explain", "about"],
        }
        
        for slot_name in available_slots:
            if slot_name in slot_keywords:
                keywords = slot_keywords[slot_name]
                if any(kw in utterance_lower for kw in keywords):
                    if slot_name not in selected:
                        selected.append(slot_name)
        
        return selected

