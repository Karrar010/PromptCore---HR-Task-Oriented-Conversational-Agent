"""
Question rewriter using Groq for natural language phrasing.
Groq ONLY rephrases questions - never changes meaning or intent.
"""

from llm.groq_client import GroqClient
from typing import Optional


class QuestionRewriter:
    """
    Rewrites system-generated questions to be more natural.
    Uses Groq for phrasing only - preserves question intent.
    """
    
    def __init__(self, groq_client: Optional[GroqClient] = None):
        """Initialize question rewriter."""
        self.groq_client = groq_client or GroqClient()
    
    def rewrite_question(
        self,
        question: str,
        intent_name: Optional[str] = None,
        slot_name: Optional[str] = None,
        user_context: Optional[str] = None
    ) -> str:
        """
        Rewrite a question to be more natural.
        Preserves the question's intent and meaning.
        Returns EXACTLY ONE sentence.
        """
        # Strict prompt to get only one sentence
        prompt = f"""You are rephrasing a system-generated question for an HR chatbot.

Rules:
- Return EXACTLY ONE sentence
- Ask EXACTLY ONE question
- Do NOT provide multiple options
- Do NOT explain
- Do NOT add prefixes like "Here are some options"
- Keep it short and professional
- Just return the rephrased question, nothing else

Input question: {question}

Output (one sentence only):"""
        
        response = self.groq_client.generate_response(
            prompt,
            max_tokens=50,
            temperature=0.5
        )
        
        # Clean up response - take only first sentence, remove quotes, remove numbering
        response = response.strip()
        
        # Remove quotes if present
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        if response.startswith("'") and response.endswith("'"):
            response = response[1:-1]
        
        # Remove numbering like "1. " or "1)" at the start
        import re
        response = re.sub(r'^\d+[\.\)]\s*', '', response)
        
        # Take only first sentence (up to period, exclamation, or question mark)
        sentences = re.split(r'[.!?]+', response)
        if sentences:
            response = sentences[0].strip()
            # Add question mark if it's a question and doesn't have punctuation
            if '?' not in response and any(word in question.lower() for word in ['what', 'when', 'where', 'who', 'why', 'how', 'which']):
                response += '?'
            elif not response.endswith(('.', '!', '?')):
                response += '.'
        
        return response if response else question

