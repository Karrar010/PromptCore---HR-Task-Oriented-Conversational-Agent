"""
Dialogue Manager that orchestrates intent detection, slot collection, and FSM transitions.
The FSM is the source of truth - this manager coordinates components but never overrides FSM logic.
"""

from typing import Optional, Dict, Any
from dialogue.fsm import FSM, FSMState
from intent.intent_router import IntentRouter
from slots.slot_selector import SlotSelector
from slots.slot_extractor import SlotExtractor
from slots.schemas import get_slot_questions, get_slot_names


class DialogueManager:
    """
    Dialogue Manager orchestrates the conversation flow.
    FSM controls all state transitions - this manager coordinates components.
    """
    
    def __init__(
        self,
        conversation_id: Optional[str] = None,
        intent_router: Optional[IntentRouter] = None,
        slot_selector: Optional[SlotSelector] = None,
        slot_extractor: Optional[SlotExtractor] = None
    ):
        """Initialize Dialogue Manager with components."""
        self.fsm = FSM(conversation_id=conversation_id)
        
        # Use provided components or try to get from pre-loaded models
        if intent_router:
            self.intent_router = intent_router
        else:
            # Try to get from pre-loaded models
            try:
                from utils.model_loader import get_model_loader
                loader = get_model_loader()
                if loader.models_loaded and loader.intent_router:
                    self.intent_router = loader.intent_router
                else:
                    self.intent_router = IntentRouter()
            except:
                self.intent_router = IntentRouter()
        
        if slot_selector:
            self.slot_selector = slot_selector
        else:
            try:
                from utils.model_loader import get_model_loader
                loader = get_model_loader()
                if loader.models_loaded and loader.slot_selector:
                    self.slot_selector = loader.slot_selector
                else:
                    self.slot_selector = SlotSelector()
            except:
                self.slot_selector = SlotSelector()
        
        if slot_extractor:
            self.slot_extractor = slot_extractor
        else:
            try:
                from utils.model_loader import get_model_loader
                loader = get_model_loader()
                if loader.models_loaded and loader.slot_extractor:
                    self.slot_extractor = loader.slot_extractor
                else:
                    self.slot_extractor = SlotExtractor()
            except:
                self.slot_extractor = SlotExtractor()
    
    def process_user_input(self, user_utterance: str) -> Dict[str, Any]:
        """
        Process user input and return response info.
        Returns dict with: {'response_text': str, 'action': str, 'metadata': dict}
        """
        if not user_utterance or not user_utterance.strip():
            return {
                'response_text': "I didn't catch that. Could you please repeat?",
                'action': 'clarify',
                'metadata': {}
            }
        
        current_state = self.fsm.get_state()
        
        # Handle termination
        if current_state == FSMState.TERMINATED:
            return {
                'response_text': "This conversation has been terminated.",
                'action': 'terminated',
                'metadata': {}
            }
        
        # Check for new intent detection (only in INIT or GENERAL_CHAT)
        if current_state in [FSMState.INIT, FSMState.GENERAL_CHAT]:
            detected_intent = self.intent_router.detect_intent(user_utterance)
            
            if detected_intent:
                # Task intent detected
                intent_set = self.fsm.set_active_intent(detected_intent)
                if not intent_set:
                    # Intent queued (another task in progress)
                    return {
                        'response_text': f"I've noted your request for {detected_intent.replace('_', ' ')}. I'll help you with that once we finish the current task.",
                        'action': 'intent_queued',
                        'metadata': {'queued_intent': detected_intent}
                    }
                
                # New intent set - start slot collection
                return self._start_slot_collection()
            else:
                # No task intent - general conversation
                if current_state == FSMState.INIT:
                    self.fsm.set_general_chat()
                return {
                    'response_text': "",  # Will be filled by Groq
                    'action': 'general_chat',
                    'metadata': {'user_utterance': user_utterance}
                }
        
        # Handle normalization confirmation
        if current_state == FSMState.CONFIRMING_NORMALIZATION:
            return self._handle_normalization_confirmation(user_utterance)
        
        # Handle slot collection
        if current_state == FSMState.COLLECTING_SLOT:
            return self._handle_slot_collection(user_utterance)
        
        # Handle ready to execute
        if current_state == FSMState.READY_TO_EXECUTE:
            # User might be confirming or providing additional info
            # Check if they're confirming execution
            if self._is_execution_confirmation(user_utterance):
                return {
                    'response_text': "Executing your request...",
                    'action': 'execute_action',
                    'metadata': {
                        'intent': self.fsm.get_active_intent(),
                        'slots': self.fsm.get_filled_slots()
                    }
                }
            else:
                # Treat as additional slot info
                return self._handle_slot_collection(user_utterance)
        
        # Default response
        return {
            'response_text': "I'm processing your request. Please wait.",
            'action': 'processing',
            'metadata': {}
        }
    
    def _start_slot_collection(self) -> Dict[str, Any]:
        """Start collecting slots for the active intent."""
        intent_name = self.fsm.get_active_intent()
        if not intent_name:
            return {'response_text': "Error: No active intent.", 'action': 'error', 'metadata': {}}
        
        next_slot = self.fsm.get_next_missing_slot(intent_name)
        if not next_slot:
            # All slots filled
            self.fsm.advance_state()
            return {
                'response_text': "I have all the information I need. Ready to proceed?",
                'action': 'ready_to_execute',
                'metadata': {}
            }
        
        self.fsm.set_current_slot(next_slot)
        slot_questions = get_slot_questions(intent_name)
        question = slot_questions[next_slot]
        
        return {
            'response_text': question,
            'action': 'ask_slot',
            'metadata': {
                'slot': next_slot,
                'intent': intent_name,
                'question': question
            }
        }
    
    def _handle_slot_collection(self, user_utterance: str) -> Dict[str, Any]:
        """Handle slot collection for current slot."""
        intent_name = self.fsm.get_active_intent()
        if not intent_name:
            return {'response_text': "Error: No active intent.", 'action': 'error', 'metadata': {}}
        
        # Get current slot being collected
        current_slot = self.fsm.state_data.current_slot_being_collected
        if not current_slot:
            current_slot = self.fsm.get_next_missing_slot(intent_name)
            self.fsm.set_current_slot(current_slot)
        
        # Select which slots this utterance can answer
        filled_slots = self.fsm.get_filled_slots()
        selected_slots = self.slot_selector.select_slots(
            user_utterance,
            intent_name,
            filled_slots
        )
        
        # IMPORTANT: If no slots selected but we have a current slot, try extracting for that slot directly
        # This handles cases where user gives a direct answer without keywords
        if not selected_slots and current_slot:
            # Try extracting for the current slot directly (context-aware)
            value = self.slot_extractor.extract_slot_value(
                user_utterance,
                current_slot,
                intent_name
            )
            if value:
                # Found a value for current slot - fill it and confirm
                self.fsm.fill_slot(current_slot, value, confirmed=False)
                self.fsm.confirm_slot(current_slot)
                self.fsm.advance_state()
                
                # Check if all slots filled
                if self.fsm.check_all_slots_filled(intent_name):
                    return {
                        'response_text': "I have all the information I need. Ready to proceed?",
                        'action': 'ready_to_execute',
                        'metadata': {}
                    }
                else:
                    # Ask for next slot
                    return self._start_slot_collection()
        
        # If still no slots selected, retry current slot
        if not selected_slots:
            if current_slot:
                retry_result = self.fsm.process_slot_collection(current_slot, None)
                
                if retry_result['action'] == 'max_retries':
                    # Skip this slot and move to next
                    # Mark slot as skipped (fill with empty or skip)
                    self.fsm.set_current_slot(None)
                    next_slot = self.fsm.get_next_missing_slot(intent_name)
                    if next_slot:
                        return self._start_slot_collection()
                    else:
                        # All slots processed (some skipped)
                        return {
                            'response_text': "I have the information I need. Ready to proceed?",
                            'action': 'ready_to_execute',
                            'metadata': {}
                        }
                else:
                    slot_questions = get_slot_questions(intent_name)
                    question = slot_questions[current_slot]
                    return {
                        'response_text': f"Could you please clarify: {question}",
                        'action': 'retry_slot',
                        'metadata': {'slot': current_slot, 'question': question}
                    }
        
        # Extract values for selected slots
        extracted_values = {}
        for slot_name in selected_slots:
            # Only extract for slots that aren't already filled
            if slot_name not in filled_slots:
                value = self.slot_extractor.extract_slot_value(
                    user_utterance,
                    slot_name,
                    intent_name
                )
                if value:
                    extracted_values[slot_name] = value
        
        # Process extracted values
        if extracted_values:
            # Fill slots and confirm them immediately (user provided the value)
            for slot_name, value in extracted_values.items():
                self.fsm.fill_slot(slot_name, value, confirmed=False)
                # Confirm the slot since user provided it
                self.fsm.confirm_slot(slot_name)
            
            # Advance state
            self.fsm.advance_state()
            
            # Check if all slots filled
            if self.fsm.check_all_slots_filled(intent_name):
                return {
                    'response_text': "I have all the information I need. Ready to proceed?",
                    'action': 'ready_to_execute',
                    'metadata': {}
                }
            else:
                # Ask for next slot
                return self._start_slot_collection()
        else:
            # No values extracted - try current slot if not already tried
            if current_slot and current_slot not in selected_slots:
                # Try extracting for current slot as fallback
                value = self.slot_extractor.extract_slot_value(
                    user_utterance,
                    current_slot,
                    intent_name
                )
                if value:
                    self.fsm.fill_slot(current_slot, value, confirmed=False)
                    self.fsm.confirm_slot(current_slot)
                    self.fsm.advance_state()
                    if self.fsm.check_all_slots_filled(intent_name):
                        return {
                            'response_text': "I have all the information I need. Ready to proceed?",
                            'action': 'ready_to_execute',
                            'metadata': {}
                        }
                    else:
                        return self._start_slot_collection()
            
            # Still no value - retry
            if current_slot:
                retry_result = self.fsm.process_slot_collection(current_slot, None)
                
                if retry_result['action'] == 'max_retries':
                    # Skip and move to next
                    self.fsm.set_current_slot(None)
                    next_slot = self.fsm.get_next_missing_slot(intent_name)
                    if next_slot:
                        return self._start_slot_collection()
                    else:
                        return {
                            'response_text': "I have the information I need. Ready to proceed?",
                            'action': 'ready_to_execute',
                            'metadata': {}
                        }
                else:
                    slot_questions = get_slot_questions(intent_name)
                    question = slot_questions[current_slot]
                    return {
                        'response_text': f"Could you please clarify: {question}",
                        'action': 'retry_slot',
                        'metadata': {'slot': current_slot, 'question': question}
                    }
        
        return {'response_text': "Processing...", 'action': 'processing', 'metadata': {}}
    
    def _handle_normalization_confirmation(self, user_utterance: str) -> Dict[str, Any]:
        """Handle normalization confirmation."""
        utterance_lower = user_utterance.lower().strip()
        
        # Check for confirmation
        if utterance_lower in ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', 'correct']:
            # Confirm normalization
            if self.fsm.state_data.pending_normalization:
                for slot_name in list(self.fsm.state_data.pending_normalization.keys()):
                    self.fsm.confirm_slot(slot_name)
            
            self.fsm.advance_state()
            return self._start_slot_collection()
        
        elif utterance_lower in ['no', 'nope', 'nah', 'incorrect', 'wrong']:
            # Reject normalization
            if self.fsm.state_data.pending_normalization:
                for slot_name in list(self.fsm.state_data.pending_normalization.keys()):
                    self.fsm.reject_normalization(slot_name)
            
            self.fsm.advance_state()
            return self._start_slot_collection()
        
        else:
            # Unclear response - ask again
            if self.fsm.state_data.pending_normalization:
                slot_name = list(self.fsm.state_data.pending_normalization.keys())[0]
                proposed_value = self.fsm.state_data.pending_normalization[slot_name]
                return {
                    'response_text': f"I proposed: {proposed_value}. Is this correct? (yes/no)",
                    'action': 'confirm_normalization',
                    'metadata': {'slot': slot_name, 'proposed_value': proposed_value}
                }
        
        return {'response_text': "Please confirm: yes or no?", 'action': 'confirm_normalization', 'metadata': {}}
    
    def _is_execution_confirmation(self, user_utterance: str) -> bool:
        """Check if user is confirming execution."""
        utterance_lower = user_utterance.lower().strip()
        confirmations = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'proceed', 'go ahead', 'execute', 'submit']
        return any(conf in utterance_lower for conf in confirmations)
    
    def propose_normalization(self, slot_name: str, proposed_value: str):
        """Propose normalized value for a slot."""
        self.fsm.set_pending_normalization(slot_name, proposed_value)
        self.fsm.transition_to(FSMState.CONFIRMING_NORMALIZATION)
    
    def execute_action(self) -> Dict[str, Any]:
        """Execute the action for the current intent."""
        intent_name = self.fsm.get_active_intent()
        if not intent_name:
            return {'success': False, 'error': 'No active intent'}
        
        if not self.fsm.check_all_slots_filled(intent_name):
            return {'success': False, 'error': 'Not all slots filled'}
        
        self.fsm.start_action_execution()
        
        return {
            'success': True,
            'intent': intent_name,
            'slots': self.fsm.get_filled_slots()
        }
    
    def complete_action(self):
        """Mark action as completed."""
        self.fsm.complete_action()
    
    def get_fsm(self) -> FSM:
        """Get the FSM instance."""
        return self.fsm
    
    def get_conversation_state(self) -> Dict[str, Any]:
        """Get current conversation state."""
        return {
            'state': self.fsm.get_state().value,
            'active_intent': self.fsm.get_active_intent(),
            'queued_intents': self.fsm.get_queued_intents(),
            'filled_slots': self.fsm.get_filled_slots(),
            'missing_slots': self.fsm.get_missing_slots(self.fsm.get_active_intent() or ''),
            'current_slot': self.fsm.state_data.current_slot_being_collected
        }

