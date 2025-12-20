"""
Finite State Machine for dialogue management.
FSM exclusively controls: active intent, queued intents, slot memory, retry counters, state transitions, termination rules.
This is a TRUE FSM, NOT if/else logic.
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from slots.schemas import get_slot_names


class FSMState(Enum):
    """FSM States - minimum required states."""
    INIT = "INIT"
    COLLECTING_SLOT = "COLLECTING_SLOT"
    CONFIRMING_NORMALIZATION = "CONFIRMING_NORMALIZATION"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    EXECUTING_ACTION = "EXECUTING_ACTION"
    COMPLETED = "COMPLETED"
    GENERAL_CHAT = "GENERAL_CHAT"
    TERMINATED = "TERMINATED"


@dataclass
class SlotValue:
    """Represents a slot value with confirmation status."""
    value: Any
    confirmed: bool = False
    retry_count: int = 0
    normalized_value: Optional[str] = None
    needs_confirmation: bool = False


@dataclass
class FSMStateData:
    """Complete FSM state data."""
    current_state: FSMState = FSMState.INIT
    active_intent: Optional[str] = None
    queued_intents: List[str] = field(default_factory=list)
    slot_values: Dict[str, SlotValue] = field(default_factory=dict)
    current_slot_being_collected: Optional[str] = None
    slot_retry_counts: Dict[str, int] = field(default_factory=dict)
    conversation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    pending_normalization: Optional[Dict[str, str]] = None  # slot_name -> proposed_value


class FSM:
    """
    True Finite State Machine for dialogue management.
    FSM exclusively controls all state transitions - deterministic and rule-based.
    """
    
    MAX_RETRIES = 3
    
    def __init__(self, conversation_id: Optional[str] = None):
        """Initialize FSM with conversation ID."""
        self.state_data = FSMStateData(conversation_id=conversation_id)
        if conversation_id:
            self.state_data.conversation_id = conversation_id
    
    def get_state(self) -> FSMState:
        """Get current FSM state."""
        return self.state_data.current_state
    
    def get_active_intent(self) -> Optional[str]:
        """Get active intent."""
        return self.state_data.active_intent
    
    def get_queued_intents(self) -> List[str]:
        """Get queued intents."""
        return self.state_data.queued_intents.copy()
    
    def get_slot_values(self) -> Dict[str, SlotValue]:
        """Get all slot values."""
        return self.state_data.slot_values.copy()
    
    def get_filled_slots(self) -> Dict[str, Any]:
        """Get confirmed slot values as plain dict."""
        return {
            name: slot.value 
            for name, slot in self.state_data.slot_values.items() 
            if slot.confirmed
        }
    
    def get_missing_slots(self, intent_name: str) -> List[str]:
        """Get list of missing slots for the active intent."""
        if not intent_name:
            return []
        
        required_slots = get_slot_names(intent_name)
        filled_slots = set(self.state_data.slot_values.keys())
        missing = [s for s in required_slots if s not in filled_slots]
        return missing
    
    def get_next_missing_slot(self, intent_name: str) -> Optional[str]:
        """Get the next missing slot to collect (one at a time)."""
        missing = self.get_missing_slots(intent_name)
        if not missing:
            return None
        
        # Return first missing slot (FSM asks for ONE at a time)
        return missing[0]
    
    def set_active_intent(self, intent_name: str) -> bool:
        """
        Set active intent. Only allowed in INIT or GENERAL_CHAT states.
        If intent is set while another task is active, queue it.
        """
        # If we're in a task flow, queue the new intent
        if self.state_data.current_state in [
            FSMState.COLLECTING_SLOT,
            FSMState.CONFIRMING_NORMALIZATION,
            FSMState.READY_TO_EXECUTE,
            FSMState.EXECUTING_ACTION
        ]:
            if intent_name not in self.state_data.queued_intents:
                self.state_data.queued_intents.append(intent_name)
            return False
        
        # Set as active intent
        self.state_data.active_intent = intent_name
        self.state_data.slot_values = {}
        self.state_data.slot_retry_counts = {}
        self.state_data.current_slot_being_collected = None
        self.state_data.pending_normalization = None
        self.transition_to(FSMState.COLLECTING_SLOT)
        return True
    
    def set_general_chat(self):
        """Set FSM to general chat mode."""
        self.state_data.active_intent = None
        self.transition_to(FSMState.GENERAL_CHAT)
    
    def fill_slot(self, slot_name: str, value: Any, confirmed: bool = False) -> bool:
        """
        Fill a slot value.
        NEVER overwrites a confirmed slot.
        Returns True if slot was filled, False if already confirmed.
        """
        if slot_name in self.state_data.slot_values:
            existing = self.state_data.slot_values[slot_name]
            if existing.confirmed:
                # NEVER overwrite confirmed slot
                return False
        
        # Set slot value
        self.state_data.slot_values[slot_name] = SlotValue(
            value=value,
            confirmed=confirmed,
            retry_count=self.state_data.slot_retry_counts.get(slot_name, 0)
        )
        self.state_data.updated_at = datetime.now()
        return True
    
    def confirm_slot(self, slot_name: str) -> bool:
        """Confirm a slot value."""
        if slot_name not in self.state_data.slot_values:
            return False
        
        self.state_data.slot_values[slot_name].confirmed = True
        self.state_data.slot_values[slot_name].needs_confirmation = False
        self.state_data.pending_normalization = None
        self.state_data.updated_at = datetime.now()
        return True
    
    def reject_normalization(self, slot_name: str):
        """Reject proposed normalization, keep original value."""
        if slot_name in self.state_data.slot_values:
            self.state_data.slot_values[slot_name].normalized_value = None
            self.state_data.slot_values[slot_name].needs_confirmation = False
        self.state_data.pending_normalization = None
        self.state_data.updated_at = datetime.now()
    
    def increment_retry(self, slot_name: str) -> bool:
        """
        Increment retry count for a slot.
        Returns True if retries remaining, False if max retries reached.
        """
        current_retries = self.state_data.slot_retry_counts.get(slot_name, 0)
        current_retries += 1
        self.state_data.slot_retry_counts[slot_name] = current_retries
        
        if slot_name in self.state_data.slot_values:
            self.state_data.slot_values[slot_name].retry_count = current_retries
        
        self.state_data.updated_at = datetime.now()
        return current_retries < self.MAX_RETRIES
    
    def set_current_slot(self, slot_name: Optional[str]):
        """Set the current slot being collected."""
        self.state_data.current_slot_being_collected = slot_name
        self.state_data.updated_at = datetime.now()
    
    def set_pending_normalization(self, slot_name: str, proposed_value: str):
        """Set pending normalization for a slot."""
        if self.state_data.pending_normalization is None:
            self.state_data.pending_normalization = {}
        self.state_data.pending_normalization[slot_name] = proposed_value
        if slot_name in self.state_data.slot_values:
            self.state_data.slot_values[slot_name].normalized_value = proposed_value
            self.state_data.slot_values[slot_name].needs_confirmation = True
        self.state_data.updated_at = datetime.now()
    
    def transition_to(self, new_state: FSMState):
        """Transition to a new state (deterministic)."""
        self.state_data.current_state = new_state
        self.state_data.updated_at = datetime.now()
    
    def check_all_slots_filled(self, intent_name: str) -> bool:
        """Check if all required slots are filled and confirmed."""
        if not intent_name:
            return False
        
        required_slots = get_slot_names(intent_name)
        for slot_name in required_slots:
            if slot_name not in self.state_data.slot_values:
                return False
            if not self.state_data.slot_values[slot_name].confirmed:
                return False
        
        return True
    
    def process_slot_collection(self, slot_name: str, extracted_value: Optional[str]) -> Dict[str, Any]:
        """
        Process slot collection attempt.
        Returns dict with action info: {'action': 'fill'|'retry'|'max_retries', 'slot': slot_name}
        """
        if not extracted_value:
            # No value extracted - retry or max retries
            can_retry = self.increment_retry(slot_name)
            if can_retry:
                return {'action': 'retry', 'slot': slot_name}
            else:
                return {'action': 'max_retries', 'slot': slot_name}
        
        # Value extracted - fill slot
        self.fill_slot(slot_name, extracted_value, confirmed=False)
        return {'action': 'fill', 'slot': slot_name, 'value': extracted_value}
    
    def advance_state(self):
        """
        Advance FSM state based on current conditions.
        This is deterministic - checks current state and transitions accordingly.
        """
        current = self.state_data.current_state
        
        if current == FSMState.INIT:
            # Stay in INIT until intent is set
            pass
        
        elif current == FSMState.COLLECTING_SLOT:
            # Check if all slots filled
            if self.state_data.active_intent:
                if self.check_all_slots_filled(self.state_data.active_intent):
                    self.transition_to(FSMState.READY_TO_EXECUTE)
                elif self.state_data.pending_normalization:
                    self.transition_to(FSMState.CONFIRMING_NORMALIZATION)
        
        elif current == FSMState.CONFIRMING_NORMALIZATION:
            # After confirmation, check if ready to execute
            if self.state_data.active_intent:
                if self.check_all_slots_filled(self.state_data.active_intent):
                    self.transition_to(FSMState.READY_TO_EXECUTE)
                else:
                    self.transition_to(FSMState.COLLECTING_SLOT)
        
        elif current == FSMState.READY_TO_EXECUTE:
            # Transition to executing when action is triggered
            pass
        
        elif current == FSMState.EXECUTING_ACTION:
            # After execution, move to completed
            self.transition_to(FSMState.COMPLETED)
        
        elif current == FSMState.COMPLETED:
            # Check for queued intents
            if self.state_data.queued_intents:
                next_intent = self.state_data.queued_intents.pop(0)
                self.set_active_intent(next_intent)
            else:
                # No queued intents, go to INIT
                self.transition_to(FSMState.INIT)
                self.state_data.active_intent = None
        
        elif current == FSMState.GENERAL_CHAT:
            # Stay in general chat until task intent detected
            pass
        
        elif current == FSMState.TERMINATED:
            # Stay terminated
            pass
    
    def start_action_execution(self):
        """Start action execution."""
        if self.state_data.current_state == FSMState.READY_TO_EXECUTE:
            self.transition_to(FSMState.EXECUTING_ACTION)
    
    def complete_action(self):
        """Mark action as completed."""
        self.transition_to(FSMState.COMPLETED)
        self.advance_state()  # Check for queued intents
    
    def terminate(self):
        """Terminate the FSM."""
        self.transition_to(FSMState.TERMINATED)
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get complete state snapshot for persistence."""
        return {
            'current_state': self.state_data.current_state.value,
            'active_intent': self.state_data.active_intent,
            'queued_intents': self.state_data.queued_intents.copy(),
            'slot_values': {
                name: {
                    'value': slot.value,
                    'confirmed': slot.confirmed,
                    'retry_count': slot.retry_count,
                    'normalized_value': slot.normalized_value,
                    'needs_confirmation': slot.needs_confirmation
                }
                for name, slot in self.state_data.slot_values.items()
            },
            'current_slot_being_collected': self.state_data.current_slot_being_collected,
            'slot_retry_counts': self.state_data.slot_retry_counts.copy(),
            'conversation_id': self.state_data.conversation_id,
            'pending_normalization': self.state_data.pending_normalization.copy() if self.state_data.pending_normalization else None,
            'updated_at': self.state_data.updated_at.isoformat()
        }
    
    def load_state_snapshot(self, snapshot: Dict[str, Any]):
        """Load state from snapshot."""
        self.state_data.current_state = FSMState(snapshot['current_state'])
        self.state_data.active_intent = snapshot.get('active_intent')
        self.state_data.queued_intents = snapshot.get('queued_intents', [])
        self.state_data.current_slot_being_collected = snapshot.get('current_slot_being_collected')
        self.state_data.slot_retry_counts = snapshot.get('slot_retry_counts', {})
        self.state_data.conversation_id = snapshot.get('conversation_id')
        self.state_data.pending_normalization = snapshot.get('pending_normalization')
        
        # Restore slot values
        slot_values_data = snapshot.get('slot_values', {})
        self.state_data.slot_values = {
            name: SlotValue(
                value=slot_data['value'],
                confirmed=slot_data['confirmed'],
                retry_count=slot_data.get('retry_count', 0),
                normalized_value=slot_data.get('normalized_value'),
                needs_confirmation=slot_data.get('needs_confirmation', False)
            )
            for name, slot_data in slot_values_data.items()
        }
        
        if snapshot.get('updated_at'):
            self.state_data.updated_at = datetime.fromisoformat(snapshot['updated_at'])

