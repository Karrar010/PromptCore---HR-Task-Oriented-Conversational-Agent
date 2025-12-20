"""
Message composer using Groq for generating action execution messages.
Groq ONLY generates message content - never chooses recipients, APIs, or triggers actions.
"""

from typing import Dict, Any, Optional, List
from llm.groq_client import GroqClient


class MessageComposer:
    """
    Composes messages for action execution.
    Groq generates message text only - all other decisions are deterministic.
    """
    
    def __init__(self, groq_client: Optional[GroqClient] = None):
        """Initialize message composer."""
        self.groq_client = groq_client or GroqClient()
    
    def compose_slack_message(
        self,
        intent_name: str,
        slot_values: Dict[str, Any],
        target_audience: str = "manager"
    ) -> str:
        """
        Compose Slack message for action execution.
        Groq generates message text only.
        """
        prompt = f"""Compose a professional Slack message for a {intent_name.replace('_', ' ')} request.

Intent: {intent_name}
Details: {self._format_slot_values(slot_values)}
Target audience: {target_audience}

Generate a clear, professional message suitable for Slack. Keep it concise and include all relevant details."""
        
        return self.groq_client.generate_response(prompt, max_tokens=200, temperature=0.6)
    
    def compose_email_message(
        self,
        intent_name: str,
        slot_values: Dict[str, Any],
        target_audience: str = "hr_department"
    ) -> str:
        """
        Compose email message for action execution.
        Groq generates message text only.
        """
        prompt = f"""Compose a professional email message for a {intent_name.replace('_', ' ')} request.

Intent: {intent_name}
Details: {self._format_slot_values(slot_values)}
Target audience: {target_audience}

Generate a clear, professional email message. Include a subject line suggestion and body."""
        
        return self.groq_client.generate_response(prompt, max_tokens=250, temperature=0.6)
    
    def compose_notification_message(
        self,
        intent_name: str,
        slot_values: Dict[str, Any],
        notification_type: str = "confirmation"
    ) -> str:
        """
        Compose notification message (SMS, push notification, etc.).
        Groq generates message text only.
        """
        prompt = f"""Compose a {notification_type} notification message for a {intent_name.replace('_', ' ')} request.

Intent: {intent_name}
Details: {self._format_slot_values(slot_values)}
Notification type: {notification_type}

Generate a brief, clear notification message. Keep it under 160 characters if possible."""
        
        return self.groq_client.generate_response(prompt, max_tokens=100, temperature=0.5)
    
    def compose_action_summary(
        self,
        intent_name: str,
        slot_values: Dict[str, Any],
        execution_status: str = "completed"
    ) -> str:
        """
        Compose action execution summary.
        Groq generates summary text only.
        """
        prompt = f"""Generate a summary message for a {intent_name.replace('_', ' ')} request that has been {execution_status}.

Intent: {intent_name}
Details: {self._format_slot_values(slot_values)}
Status: {execution_status}

Generate a friendly, informative summary message for the user."""
        
        return self.groq_client.generate_response(prompt, max_tokens=150, temperature=0.7)
    
    def _format_slot_values(self, slot_values: Dict[str, Any]) -> str:
        """Format slot values for prompt."""
        formatted = []
        for key, value in slot_values.items():
            formatted.append(f"{key.replace('_', ' ').title()}: {value}")
        return "\n".join(formatted)

