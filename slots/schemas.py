"""
Central schema definitions for all task intents.
Schemas are immutable and centrally stored.
"""

from typing import Dict, List, TypedDict
from dataclasses import dataclass


@dataclass
class SlotSchema:
    """Schema for a single slot."""
    name: str
    question: str
    required: bool = True


@dataclass
class IntentSchema:
    """Schema for an intent with its slots."""
    intent_name: str
    slots: List[SlotSchema]


# Central schema registry - IMMUTABLE
TASK_SCHEMAS: Dict[str, IntentSchema] = {
    "request_time_off": IntentSchema(
        intent_name="request_time_off",
        slots=[
            SlotSchema("employee_name", "What is your name?"),
            SlotSchema("start_date", "When would you like to start your time off?"),
            SlotSchema("end_date", "When would you like to return?"),
            SlotSchema("time_off_type", "What type of time off is this? (e.g., vacation, sick, personal)"),
            SlotSchema("reason", "What is the reason for this time off request?"),
            SlotSchema("notify_manager", "Should we notify your manager? (yes/no)"),
        ]
    ),
    "schedule_meeting": IntentSchema(
        intent_name="schedule_meeting",
        slots=[
            SlotSchema("organizer_name", "Who is organizing this meeting?"),
            SlotSchema("date", "What date should the meeting be scheduled?"),
            SlotSchema("start_time", "What time should the meeting start?"),
            SlotSchema("end_time", "What time should the meeting end?"),
            SlotSchema("participants", "Who should attend this meeting?"),
            SlotSchema("meeting_platform", "Which platform should be used? (e.g., Zoom, Teams, Google Meet)"),
            SlotSchema("agenda", "What is the agenda for this meeting?"),
        ]
    ),
    "submit_it_ticket": IntentSchema(
        intent_name="submit_it_ticket",
        slots=[
            SlotSchema("requester_name", "What is your name?"),
            SlotSchema("issue_category", "What category does this issue fall under? (e.g., hardware, software, network)"),
            SlotSchema("issue_description", "Please describe the issue in detail."),
            SlotSchema("urgency", "What is the urgency level? (low, medium, high, critical)"),
            SlotSchema("affected_system", "Which system is affected?"),
            SlotSchema("contact_email", "What is your contact email?"),
        ]
    ),
    "file_medical_claim": IntentSchema(
        intent_name="file_medical_claim",
        slots=[
            SlotSchema("employee_name", "What is your name?"),
            SlotSchema("incident_date", "When did the medical incident occur?"),
            SlotSchema("provider_name", "What is the name of the healthcare provider?"),
            SlotSchema("claim_amount", "What is the claim amount?"),
            SlotSchema("claim_type", "What type of claim is this? (e.g., doctor visit, prescription, procedure)"),
            SlotSchema("description", "Please describe the medical claim."),
        ]
    ),
}


def get_schema(intent_name: str) -> IntentSchema:
    """Get schema for an intent."""
    if intent_name not in TASK_SCHEMAS:
        raise ValueError(f"Unknown intent: {intent_name}")
    return TASK_SCHEMAS[intent_name]


def get_slot_names(intent_name: str) -> List[str]:
    """Get list of slot names for an intent."""
    schema = get_schema(intent_name)
    return [slot.name for slot in schema.slots]


def get_slot_questions(intent_name: str) -> Dict[str, str]:
    """Get mapping of slot names to questions for an intent."""
    schema = get_schema(intent_name)
    return {slot.name: slot.question for slot in schema.slots}

