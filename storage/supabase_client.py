"""
Supabase client for persistence and audit layer.
Supabase stores: conversations, FSM state snapshots, slot values, action execution logs, messages.
Supabase NEVER decides logic, triggers transitions, or replaces FSM memory.
"""

from typing import Optional, Dict, Any, List
import os
from supabase import create_client, Client
from datetime import datetime
import json


class SupabaseClient:
    """
    Supabase client for persistence.
    FSM is source of truth - Supabase mirrors FSM state.
    """
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        """Initialize Supabase client."""
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            print("Warning: Supabase credentials not provided. Storage will be disabled.")
            self.client: Optional[Client] = None
        else:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                print(f"Error initializing Supabase client: {e}")
                self.client = None
    
    def is_available(self) -> bool:
        """Check if Supabase is available."""
        return self.client is not None
    
    def save_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
        channel: Optional[str] = None,
        platform: Optional[str] = None
    ) -> bool:
        """Save conversation metadata."""
        if not self.is_available():
            return False
        
        try:
            # Use upsert to create or update conversation
            # This ensures the conversation exists before messages are saved
            self.client.table("conversations").upsert({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "channel": channel,
                "platform": platform,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="conversation_id").execute()
            return True
        except Exception as e:
            # Silently fail if conversation already exists or other non-critical errors
            # Only print if it's a real issue
            error_str = str(e)
            if "duplicate key" not in error_str.lower() and "already exists" not in error_str.lower():
                print(f"Error saving conversation: {e}")
            return False
    
    def save_fsm_state(
        self,
        conversation_id: str,
        state_snapshot: Dict[str, Any]
    ) -> bool:
        """Save FSM state snapshot."""
        if not self.is_available():
            return False
        
        try:
            self.client.table("fsm_states").upsert({
                "conversation_id": conversation_id,
                "state_snapshot": json.dumps(state_snapshot),
                "updated_at": datetime.now().isoformat()
            }).execute()
            return True
        except Exception as e:
            print(f"Error saving FSM state: {e}")
            return False
    
    def load_fsm_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load FSM state snapshot."""
        if not self.is_available():
            return None
        
        try:
            response = self.client.table("fsm_states").select("*").eq("conversation_id", conversation_id).order("updated_at", desc=True).limit(1).execute()
            
            if response.data:
                snapshot_str = response.data[0]["state_snapshot"]
                return json.loads(snapshot_str)
            
            return None
        except Exception as e:
            print(f"Error loading FSM state: {e}")
            return None
    
    def save_message(
        self,
        conversation_id: str,
        message_type: str,  # 'user' or 'bot'
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save message to conversation log."""
        if not self.is_available():
            return False
        
        try:
            # Ensure conversation exists first (upsert will create if not exists)
            try:
                self.client.table("conversations").upsert({
                    "conversation_id": conversation_id,
                    "updated_at": datetime.now().isoformat()
                }, on_conflict="conversation_id").execute()
            except:
                pass  # Ignore if conversation already exists or error
            
            self.client.table("messages").insert({
                "conversation_id": conversation_id,
                "message_type": message_type,
                "content": content,
                "metadata": json.dumps(metadata) if metadata else None,
                "created_at": datetime.now().isoformat()
            }).execute()
            return True
        except Exception as e:
            # Only print error if it's not a foreign key constraint (conversation should exist now)
            error_str = str(e)
            if "foreign key" not in error_str.lower():
                print(f"Error saving message: {e}")
            return False
    
    def save_action_execution(
        self,
        conversation_id: str,
        intent_name: str,
        slot_values: Dict[str, Any],
        execution_status: str,  # 'success' or 'failure'
        message_content: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Save action execution log."""
        if not self.is_available():
            return False
        
        try:
            self.client.table("action_executions").insert({
                "conversation_id": conversation_id,
                "intent_name": intent_name,
                "slot_values": json.dumps(slot_values),
                "execution_status": execution_status,
                "message_content": message_content,
                "error_message": error_message,
                "executed_at": datetime.now().isoformat()
            }).execute()
            return True
        except Exception as e:
            print(f"Error saving action execution: {e}")
            return False
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation message history."""
        if not self.is_available():
            return []
        
        try:
            response = self.client.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).limit(limit).execute()
            return response.data or []
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []

