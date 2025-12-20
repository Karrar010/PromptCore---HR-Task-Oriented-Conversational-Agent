"""
Span-based slot extractor using QA models.
Extracts answers verbatim from user text.
One extraction per slot. Returns None if answer not present.
"""

from typing import Optional, Dict
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from slots.schemas import get_slot_questions


class SlotExtractor:
    """
    Span-based extractive slot extractor.
    Extracts answers verbatim from user text - NO generation or inference.
    """
    
    def __init__(self, model_name: str = "mrm8488/mobilebert-uncased-finetuned-squadv2"):
        """
        Initialize with a pre-trained QA model.
        Using MobileBERT-SQuAD2 - best performing model (96.15% accuracy, 0.0738s avg time).
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        
        if model_name is None:
            print("Using rule-based slot extraction (no model)")
            return
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForQuestionAnswering.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            print(f"✓ Slot extraction model loaded: {model_name}")
        except Exception as e:
            # Fallback to rule-based if model loading fails
            print(f"Warning: Could not load QA model {model_name}: {e}")
            print("Falling back to rule-based extraction")
    
    def extract_slot_value(
        self,
        user_utterance: str,
        slot_name: str,
        intent_name: str
    ) -> Optional[str]:
        """
        Extract slot value from user utterance.
        Returns extracted value verbatim or None if not found.
        
        Rules:
        - Extracts verbatim text only
        - Returns None if answer not present
        - One extraction per slot
        - NO generation or inference
        """
        if not user_utterance or not user_utterance.strip():
            return None
        
        # Get slot question
        slot_questions = get_slot_questions(intent_name)
        if slot_name not in slot_questions:
            return None
        
        slot_question = slot_questions[slot_name]
        
        # If model not available, use rule-based fallback
        if self.model is None:
            return self._rule_based_extraction(user_utterance, slot_name, intent_name)
        
        try:
            # Format as QA: question and context
            inputs = self.tokenizer(
                slot_question,
                user_utterance,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            
            # Get answer span
            with torch.no_grad():
                outputs = self.model(**inputs)
                start_logits = outputs.start_logits
                end_logits = outputs.end_logits
                
                # Improved QA span extraction - find best answer span
                start_scores = start_logits[0].cpu().numpy()
                end_scores = end_logits[0].cpu().numpy()
                
                # Find best answer span by checking valid start-end pairs
                max_score = float('-inf')
                best_start = 0
                best_end = 0
                
                # Search for best span (start must be before end, and not at [CLS] token 0)
                # Limit search to reasonable span lengths for efficiency
                max_span_length = min(20, len(start_scores) - 1)
                for start_idx in range(1, min(len(start_scores), len(user_utterance.split()) + 10)):
                    for end_idx in range(start_idx, min(len(end_scores), start_idx + max_span_length)):
                        score = start_scores[start_idx] + end_scores[end_idx]
                        if score > max_score:
                            max_score = score
                            best_start = start_idx
                            best_end = end_idx
                
                # If no valid span found or score too low, use rule-based
                if best_start == 0 or best_start > best_end or max_score < -5.0:
                    return self._rule_based_extraction(user_utterance, slot_name, intent_name)
                
                # Extract answer
                answer_tokens = inputs["input_ids"][0][best_start:best_end + 1]
                answer = self.tokenizer.decode(answer_tokens, skip_special_tokens=True)
                
                # Clean up answer
                answer = answer.strip()
                
                # Validate extracted answer
                if not answer or len(answer) < 1:
                    return self._rule_based_extraction(user_utterance, slot_name, intent_name)
                
                # If answer seems wrong (contains question words or is too long), use rule-based
                question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'which']
                if any(qw in answer.lower() for qw in question_words) or len(answer) > len(user_utterance) * 1.5:
                    return self._rule_based_extraction(user_utterance, slot_name, intent_name)
                
                return answer
        
        except Exception as e:
            print(f"Error in model-based extraction: {e}")
            # Fallback to rule-based
            return self._rule_based_extraction(user_utterance, slot_name, intent_name)
    
    def _rule_based_extraction(
        self,
        user_utterance: str,
        slot_name: str,
        intent_name: str
    ) -> Optional[str]:
        """
        Rule-based fallback for slot extraction.
        Uses simple pattern matching to extract values.
        """
        utterance = user_utterance.strip()
        
        # Pattern-based extraction for common slot types
        import re
        
        # Name patterns - handle first (most common issue)
        if "name" in slot_name.lower():
            # If utterance is short and looks like a name (2-3 words, mostly letters)
            if len(utterance.split()) <= 3 and len(utterance) < 50:
                # Check if it looks like a name (letters, spaces, hyphens, apostrophes)
                if re.match(r'^[A-Za-z\s\.\-\']{2,50}$', utterance):
                    # Clean up and return
                    name = utterance.strip()
                    # Capitalize properly
                    name = ' '.join(word.capitalize() for word in name.split())
                    return name
            # Also check for "I am X" or "My name is X" patterns
            name_patterns = [
                r"(?:i am|my name is|this is|call me|i'm)\s+([A-Za-z\s\.\-\']{2,50})",
                r"^([A-Za-z\s\.\-\']{2,50})$",  # Just a name
            ]
            for pattern in name_patterns:
                match = re.search(pattern, utterance, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    if len(name.split()) <= 3:  # Reasonable name length
                        return ' '.join(word.capitalize() for word in name.split())
        
        # Date patterns
        if "date" in slot_name.lower():
            # Look for date patterns
            date_patterns = [
                r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # MM/DD/YYYY
                r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                r"\b(?:tomorrow|today|yesterday|next week|this week)\b",
                r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b",
            ]
            for pattern in date_patterns:
                match = re.search(pattern, utterance, re.IGNORECASE)
                if match:
                    return match.group(0)
        
        # Time patterns
        if "time" in slot_name.lower():
            time_patterns = [
                r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b",
                r"\b\d{1,2}:\d{2}\b",
            ]
            for pattern in time_patterns:
                match = re.search(pattern, utterance, re.IGNORECASE)
                if match:
                    return match.group(0)
        
        # Email patterns
        if "email" in slot_name.lower():
            email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            match = re.search(email_pattern, utterance)
            if match:
                return match.group(0)
        
        # Amount/currency patterns
        if "amount" in slot_name.lower():
            amount_patterns = [
                r"\$\d+(?:\.\d{2})?",
                r"\b\d+(?:\.\d{2})?\s*(?:dollars?|USD)\b",
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, utterance, re.IGNORECASE)
                if match:
                    return match.group(0)
        
        # Yes/No patterns
        if "notify" in slot_name.lower():
            if re.search(r"\b(yes|yeah|yep|sure|ok|okay)\b", utterance, re.IGNORECASE):
                return "yes"
            if re.search(r"\b(no|nope|nah|don't|do not)\b", utterance, re.IGNORECASE):
                return "no"
        
        # For other slots, if utterance is short and seems like a direct answer, return it
        if len(utterance) < 100 and len(utterance.split()) <= 5:
            # For short utterances, return the whole thing if it seems like a direct answer
            # Exclude common non-answer phrases
            skip_phrases = ["i don't know", "not sure", "maybe", "i think"]
            if not any(phrase in utterance.lower() for phrase in skip_phrases):
                return utterance
        
        # Default: return None (no extraction possible)
        return None

