"""
Intent router using Groq LLM for intent classification.
Uses Groq for intent detection for the 4 task intents.
Falls back to rule-based if Groq fails.
"""

import re
from typing import Optional, List, Dict
import os
from groq import Groq


class IntentRouter:
    """
    Model-based intent detection using Hugging Face models.
    Returns exactly one active intent at a time.
    Falls back to rule-based if models unavailable.
    """
    
    def __init__(self, groq_client=None):
        """
        Initialize with Groq LLM for intent detection.
        Uses Groq to detect which of the 4 task intents the user wants.
        Falls back to rule-based if Groq fails.
        """
        self.use_groq = False
        self.groq_client = None
        
        # Intent labels for classification
        self.intent_labels = [
            "request_time_off",
            "schedule_meeting",
            "submit_it_ticket",
            "file_medical_claim"
        ]
        
        # Intent descriptions for Groq
        self.intent_descriptions = {
            "request_time_off": "Request time off, vacation, leave, PTO, sick leave, or personal days",
            "schedule_meeting": "Schedule a meeting, appointment, or calendar event",
            "submit_it_ticket": "Submit IT ticket, report technical issue, computer problem, or IT support request",
            "file_medical_claim": "File medical claim, health insurance claim, or medical expense reimbursement"
        }
        
        # Try to initialize Groq client
        if groq_client:
            self.groq_client = groq_client
            self.use_groq = True
            print("✓ Intent detection using Groq LLM")
        else:
            try:
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    from groq import Groq
                    self.groq_client = Groq(api_key=api_key)
                    self.use_groq = True
                    print("✓ Intent detection using Groq LLM")
                else:
                    print("Warning: GROQ_API_KEY not found. Falling back to rule-based intent detection")
            except Exception as e:
                print(f"Warning: Could not initialize Groq client: {e}")
                print("Falling back to rule-based intent detection")
        
        # Rule-based fallback patterns
        self.intent_patterns: Dict[str, List[Dict[str, any]]] = {
            "request_time_off": [
                {"keywords": ["time off", "vacation", "leave", "day off", "pto", "sick leave", "personal day"], "weight": 3},
                {"keywords": ["request", "need", "want", "take"], "weight": 1},
                {"patterns": [r"\b(off|leave|vacation)\b", r"\b(tomorrow|next week|monday|friday)\b"], "weight": 2},
            ],
            "schedule_meeting": [
                {"keywords": ["meeting", "schedule", "book", "calendar", "appointment"], "weight": 3},
                {"keywords": ["set up", "arrange", "organize"], "weight": 2},
                {"patterns": [r"\b(meeting|appointment)\b", r"\b(schedule|book|set)\b"], "weight": 2},
            ],
            "submit_it_ticket": [
                {"keywords": ["it ticket", "it issue", "technical", "computer", "laptop", "software", "hardware"], "weight": 3},
                {"keywords": ["problem", "broken", "not working", "error", "bug"], "weight": 2},
                {"keywords": ["submit", "file", "report"], "weight": 1},
                {"patterns": [r"\b(it|tech|technical)\b.*\b(issue|problem|ticket)\b"], "weight": 3},
            ],
            "file_medical_claim": [
                {"keywords": ["medical claim", "health insurance", "doctor", "hospital", "prescription"], "weight": 3},
                {"keywords": ["claim", "reimbursement", "medical expense"], "weight": 2},
                {"keywords": ["file", "submit", "process"], "weight": 1},
                {"patterns": [r"\b(medical|health)\b.*\b(claim|expense)\b"], "weight": 3},
            ],
        }
        
        # General HR conversation patterns (non-task)
        self.general_patterns = [
            {"keywords": ["hello", "hi", "hey", "help", "question", "ask"], "weight": 1},
            {"keywords": ["policy", "benefits", "hr", "information"], "weight": 1},
        ]
    
    def detect_intent(self, user_utterance: str) -> Optional[str]:
        """
        Detect intent from user utterance using Groq LLM or rule-based fallback.
        Returns intent name or None if no task intent detected.
        
        Rules:
        - Returns exactly one intent
        - Task intents take priority over general conversation
        - Returns None if no clear task intent (will default to general_hr_conversation)
        """
        if not user_utterance or not user_utterance.strip():
            return None
        
        # Try Groq-based detection first
        if self.use_groq and self.groq_client is not None:
            try:
                return self._groq_based_detection(user_utterance)
            except Exception as e:
                print(f"Error in Groq-based intent detection: {e}")
                # Fall through to rule-based
        
        # Rule-based fallback
        return self._rule_based_detection(user_utterance)
    
    def _groq_based_detection(self, user_utterance: str) -> Optional[str]:
        """Detect intent using Groq LLM."""
        try:
            # Create prompt for Groq
            intent_list = "\n".join([f"- {intent}: {desc}" for intent, desc in self.intent_descriptions.items()])
            
            prompt = f"""You are an intent classifier for an HR chatbot. Analyze the user's message and determine which of the following 4 task intents they want, or return "none" if it doesn't match any task intent.

Available task intents:
{intent_list}

User message: "{user_utterance}"

Instructions:
- Return ONLY the intent name (e.g., "request_time_off", "schedule_meeting", "submit_it_ticket", "file_medical_claim") or "none"
- Be precise - only return an intent if the user clearly wants to perform that task
- If the message is just a greeting, question, or general conversation, return "none"
- Return ONLY the intent name, nothing else

Intent:"""

            # Use the Groq client's underlying client
            response = self.groq_client.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a precise intent classifier. Return only the intent name or 'none'."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,
                temperature=0.1  # Low temperature for deterministic classification
            )
            
            intent_name = response.choices[0].message.content.strip().lower()
            
            # Clean up response
            intent_name = intent_name.replace('"', '').replace("'", "").strip()
            
            # Check if it's a valid intent
            if intent_name in self.intent_labels:
                return intent_name
            elif intent_name == "none" or intent_name == "":
                return None
            else:
                # Try to match partial names
                for label in self.intent_labels:
                    if label in intent_name or intent_name in label:
                        return label
                return None
            
        except Exception as e:
            print(f"Error in Groq intent detection: {e}")
            return None
    
    def _rule_based_detection(self, user_utterance: str) -> Optional[str]:
        """Rule-based intent detection fallback."""
        utterance_lower = user_utterance.lower()
        intent_scores: Dict[str, float] = {}
        
        # Score each task intent
        for intent_name, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern_group in patterns:
                if "keywords" in pattern_group:
                    for keyword in pattern_group["keywords"]:
                        if keyword in utterance_lower:
                            score += pattern_group["weight"]
                
                if "patterns" in pattern_group:
                    for pattern in pattern_group["patterns"]:
                        if re.search(pattern, utterance_lower, re.IGNORECASE):
                            score += pattern_group["weight"]
            
            if score > 0:
                intent_scores[intent_name] = score
        
        # Return highest scoring intent if threshold met
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            # Minimum threshold to avoid false positives
            if best_intent[1] >= 2.0:
                return best_intent[0]
        
        # No task intent detected
        return None
    
    def is_task_intent(self, intent: Optional[str]) -> bool:
        """Check if intent is a task intent (not general conversation)."""
        if intent is None:
            return False
        return intent in self.intent_patterns
    
    def get_supported_intents(self) -> List[str]:
        """Get list of all supported task intents."""
        return list(self.intent_patterns.keys())

