"""
Twilio service for sending SMS notifications.
Deterministic action execution - no LLM reasoning.
"""

from typing import Optional, Dict, Any
import os
from twilio.rest import Client as TwilioClient


class TwilioService:
    """
    Twilio service for sending SMS messages.
    Deterministic - executes actions based on intent and slots.
    """
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None
    ):
        """Initialize Twilio service."""
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv("TWILIO_FROM_NUMBER")
        
        if self.account_sid and self.auth_token:
            try:
                self.client = TwilioClient(self.account_sid, self.auth_token)
            except Exception as e:
                print(f"Error initializing Twilio client: {e}")
                self.client = None
        else:
            print("Warning: Twilio credentials not provided. SMS will be disabled.")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Twilio is available."""
        return self.client is not None
    
    def send_sms(
        self,
        to_number: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send SMS message.
        Returns: {'success': bool, 'sid': str, 'error': str}
        """
        if not self.is_available():
            return {
                'success': False,
                'sid': None,
                'error': 'Twilio client not available'
            }
        
        if not self.from_number:
            return {
                'success': False,
                'sid': None,
                'error': 'Twilio from_number not configured'
            }
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            return {
                'success': True,
                'sid': message_obj.sid,
                'error': None
            }
        
        except Exception as e:
            return {
                'success': False,
                'sid': None,
                'error': str(e)
            }
    
    def send_notification(
        self,
        phone_number: str,
        notification_text: str
    ) -> Dict[str, Any]:
        """
        Send notification SMS.
        Wrapper around send_sms for consistency.
        """
        return self.send_sms(phone_number, notification_text)
    
    def execute_action_notification(
        self,
        intent_name: str,
        slot_values: Dict[str, Any],
        phone_number: str,
        message_content: str
    ) -> Dict[str, Any]:
        """
        Execute action notification via SMS.
        Sends confirmation or status update.
        """
        return self.send_sms(phone_number, message_content)

