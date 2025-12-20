"""
Main application entry point for HR task-oriented conversational agent.
Orchestrates all components according to the strict architecture.
"""

import os
import uuid
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from dialogue.dialogue_manager import DialogueManager
from dialogue.fsm import FSMState
from llm.groq_client import GroqClient
from llm.question_rewriter import QuestionRewriter
from llm.normalizer import SlotNormalizer
from llm.message_composer import MessageComposer
from storage.conversation_store import ConversationStore
from actions.slack_service import SlackService
from actions.twilio_service import TwilioService

# Load environment variables from .env file
load_dotenv()


class HRConversationalAgent:
    """
    Main HR conversational agent.
    Orchestrates all components according to strict architecture.
    """
    
    def __init__(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        channel: Optional[str] = None,
        platform: Optional[str] = None
    ):
        """Initialize HR conversational agent."""
        # Generate conversation ID if not provided
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.channel = channel
        self.platform = platform
        
        # Try to get pre-loaded Groq client, otherwise create new one
        try:
            from utils.model_loader import get_model_loader
            loader = get_model_loader()
            if loader.models_loaded and loader.groq_client:
                self.groq_client = loader.groq_client
            else:
                self.groq_client = GroqClient()
        except:
            self.groq_client = GroqClient()
        
        self.question_rewriter = QuestionRewriter(self.groq_client)
        self.normalizer = SlotNormalizer(self.groq_client)
        self.message_composer = MessageComposer(self.groq_client)
        
        self.conversation_store = ConversationStore()
        self.slack_service = SlackService()
        self.twilio_service = TwilioService()
        
        # Initialize dialogue manager (will use pre-loaded models if available)
        self.dialogue_manager = DialogueManager(conversation_id=self.conversation_id)
        
        # Load conversation state if exists
        self._load_conversation_state()
    
    def _load_conversation_state(self):
        """Load conversation state from storage."""
        state_snapshot = self.conversation_store.load_conversation_state(self.conversation_id)
        if state_snapshot:
            self.dialogue_manager.get_fsm().load_state_snapshot(state_snapshot)
    
    def _save_conversation_state(self):
        """Save conversation state to storage."""
        self.conversation_store.save_conversation_state(
            conversation_id=self.conversation_id,
            fsm=self.dialogue_manager.get_fsm(),
            user_id=self.user_id,
            channel=self.channel,
            platform=self.platform
        )
    
    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process user message and return response.
        Returns: {'response_text': str, 'action': str, 'metadata': dict}
        """
        # Ensure conversation exists in database FIRST (before messages)
        self._save_conversation_state()
        
        # Save user message
        self.conversation_store.save_user_message(
            conversation_id=self.conversation_id,
            content=user_message
        )
        
        # Process through dialogue manager
        result = self.dialogue_manager.process_user_input(user_message)
        
        # Enhance response with Groq if needed
        response_text = result.get('response_text', '')
        action = result.get('action', '')
        metadata = result.get('metadata', {})
        
        # Handle general chat
        if action == 'general_chat':
            response_text = self.groq_client.generate_conversational_response(
                user_message,
                context=f"Conversation ID: {self.conversation_id}"
            )
        
        # Rewrite questions for better UX
        if action in ['ask_slot', 'retry_slot'] and response_text:
            slot_name = metadata.get('slot')
            intent_name = metadata.get('intent')
            response_text = self.question_rewriter.rewrite_question(
                response_text,
                intent_name=intent_name,
                slot_name=slot_name,
                user_context=user_message
            )
        
        # Handle normalization
        if action == 'fill' and 'slot' in metadata:
            slot_name = metadata['slot']
            value = metadata.get('value', '')
            
            # Check if normalization needed
            if self.normalizer.needs_normalization(slot_name, value):
                proposed_value = self.normalizer.normalize_value(
                    slot_name,
                    value,
                    intent_name=self.dialogue_manager.get_fsm().get_active_intent()
                )
                
                if proposed_value:
                    # Propose normalization
                    self.dialogue_manager.propose_normalization(slot_name, proposed_value)
                    
                    # Generate clarification question
                    clarification = self.normalizer.generate_clarification_question(
                        slot_name,
                        value,
                        proposed_value
                    )
                    
                    response_text = clarification
                    action = 'confirm_normalization'
                    metadata['proposed_value'] = proposed_value
        
        # Handle action execution
        if action == 'execute_action':
            execution_result = self._execute_action(
                intent_name=metadata.get('intent'),
                slot_values=metadata.get('slots', {})
            )
            
            if execution_result['success']:
                response_text = execution_result.get('summary', 'Your request has been processed successfully.')
            else:
                response_text = f"I encountered an error: {execution_result.get('error', 'Unknown error')}"
            
            action = 'action_completed'
            metadata['execution_result'] = execution_result
        
        # Save bot response
        self.conversation_store.save_bot_message(
            conversation_id=self.conversation_id,
            content=response_text,
            metadata={'action': action, **metadata}
        )
        
        # Save conversation state
        self._save_conversation_state()
        
        return {
            'response_text': response_text,
            'action': action,
            'metadata': metadata,
            'conversation_id': self.conversation_id
        }
    
    def _execute_action(
        self,
        intent_name: str,
        slot_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute action based on intent and slot values.
        Deterministic execution - no LLM reasoning.
        """
        try:
            # Use Groq to compose message and determine execution strategy
            # Groq helps with message content, but APIs handle actual execution
            
            if intent_name == "request_time_off":
                # Compose message using Groq
                message_content = self.message_composer.compose_slack_message(
                    intent_name=intent_name,
                    slot_values=slot_values,
                    target_audience="manager"
                )
                
                # Execute via Slack API (will auto-discover channels)
                result = self.slack_service.execute_request_time_off(
                    message_content=message_content,
                    employee_name=slot_values.get('employee_name', 'Employee'),
                    manager_channel=self.channel or os.getenv("MANAGER_CHANNEL"),
                    manager_user_id=os.getenv("MANAGER_USER_ID")
                )
            
            elif intent_name == "schedule_meeting":
                # Compose message using Groq
                message_content = self.message_composer.compose_slack_message(
                    intent_name=intent_name,
                    slot_values=slot_values,
                    target_audience="meeting_participants"
                )
                
                # Parse participants and execute via Slack API
                participants = slot_values.get('participants', '')
                if isinstance(participants, str):
                    participants = [p.strip() for p in participants.split(',') if p.strip()]
                
                result = self.slack_service.execute_schedule_meeting(
                    message_content=message_content,
                    participants=participants,
                    channel=self.channel or os.getenv("MEETING_CHANNEL")
                )
            
            elif intent_name == "submit_it_ticket":
                # Compose message using Groq with IT-specific formatting
                message_content = self.message_composer.compose_slack_message(
                    intent_name=intent_name,
                    slot_values=slot_values,
                    target_audience="it_support"
                )
                
                # Find best IT channel using workspace discovery
                best_channel = self.slack_service.get_best_channel_for_intent(intent_name)
                it_channel = best_channel or os.getenv("IT_CHANNEL")
                it_user_id = os.getenv("IT_USER_ID")
                
                # Execute via Slack API
                result = self.slack_service.execute_submit_it_ticket(
                    message_content=message_content,
                    it_channel=it_channel,
                    it_user_id=it_user_id
                )
            
            elif intent_name == "file_medical_claim":
                # Compose message using Groq
                message_content = self.message_composer.compose_slack_message(
                    intent_name=intent_name,
                    slot_values=slot_values,
                    target_audience="hr_department"
                )
                
                # Find best HR channel using workspace discovery
                best_channel = self.slack_service.get_best_channel_for_intent(intent_name)
                hr_channel = best_channel or self.channel or os.getenv("HR_CHANNEL")
                
                # Execute via Slack API
                result = self.slack_service.execute_file_medical_claim(
                    message_content=message_content,
                    hr_channel=hr_channel,
                    hr_user_id=os.getenv("HR_USER_ID")
                )
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown intent: {intent_name}'
                }
            
            # Generate summary
            execution_status = "completed" if result.get('success') else "failed"
            note = result.get('note', '')
            
            if result.get('success'):
                if note:
                    summary = f"Your request has been processed successfully. {note}"
                else:
                    summary = self.message_composer.compose_action_summary(
                        intent_name=intent_name,
                        slot_values=slot_values,
                        execution_status=execution_status
                    )
            else:
                summary = f"I encountered an issue: {result.get('error', 'Unknown error')}"
            
            # Save action execution log
            self.conversation_store.save_action_log(
                conversation_id=self.conversation_id,
                intent_name=intent_name,
                slot_values=slot_values,
                execution_status="success" if result.get('success') else "failure",
                message_content=message_content,
                error_message=result.get('error')
            )
            
            # Mark action as completed in FSM only if successful
            if result.get('success'):
                self.dialogue_manager.complete_action()
            
            return {
                'success': result.get('success', False),
                'summary': summary,
                'error': result.get('error')
            }
        
        except Exception as e:
            # Save error log
            self.conversation_store.save_action_log(
                conversation_id=self.conversation_id,
                intent_name=intent_name,
                slot_values=slot_values,
                execution_status="failure",
                error_message=str(e)
            )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_conversation_state(self) -> Dict[str, Any]:
        """Get current conversation state."""
        return self.dialogue_manager.get_conversation_state()


# Main entry point removed - use interface/app.py instead
# This module provides the HRConversationalAgent class for use by the web interface

