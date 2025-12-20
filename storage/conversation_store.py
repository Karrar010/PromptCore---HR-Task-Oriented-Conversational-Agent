"""
Conversation store that wraps Supabase client.
Provides high-level interface for conversation persistence.
"""

from typing import Optional, Dict, Any
from storage.supabase_client import SupabaseClient
from dialogue.fsm import FSM


class ConversationStore:
    """
    High-level conversation store interface.
    Wraps Supabase client for conversation persistence.
    """
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """Initialize conversation store."""
        self.supabase = supabase_client or SupabaseClient()
    
    def save_conversation_state(
        self,
        conversation_id: str,
        fsm: FSM,
        user_id: Optional[str] = None,
        channel: Optional[str] = None,
        platform: Optional[str] = None
    ) -> bool:
        """Save complete conversation state."""
        # Save conversation metadata
        self.supabase.save_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            channel=channel,
            platform=platform
        )
        
        # Save FSM state snapshot
        state_snapshot = fsm.get_state_snapshot()
        return self.supabase.save_fsm_state(conversation_id, state_snapshot)
    
    def load_conversation_state(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load conversation state snapshot."""
        return self.supabase.load_fsm_state(conversation_id)
    
    def save_user_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save user message."""
        return self.supabase.save_message(
            conversation_id=conversation_id,
            message_type="user",
            content=content,
            metadata=metadata
        )
    
    def save_bot_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save bot message."""
        return self.supabase.save_message(
            conversation_id=conversation_id,
            message_type="bot",
            content=content,
            metadata=metadata
        )
    
    def save_action_log(
        self,
        conversation_id: str,
        intent_name: str,
        slot_values: Dict[str, Any],
        execution_status: str,
        message_content: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Save action execution log."""
        return self.supabase.save_action_execution(
            conversation_id=conversation_id,
            intent_name=intent_name,
            slot_values=slot_values,
            execution_status=execution_status,
            message_content=message_content,
            error_message=error_message
        )
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> list:
        """Get conversation history."""
        return self.supabase.get_conversation_history(conversation_id, limit)

