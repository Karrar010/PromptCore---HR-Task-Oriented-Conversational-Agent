"""
Groq LLM client for natural language generation.
Groq is used ONLY for UX - rephrasing questions, empathy, conversational responses.
Groq NEVER decides intent, slot order, extracts values, modifies schemas, or controls FSM.
"""

from typing import Optional, Dict, Any
import os
from groq import Groq


class GroqClient:
    """
    Groq LLM client.
    Used ONLY for natural language generation - NOT for logic or decision-making.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Groq client."""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables. Please set it in .env file.")
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-8b-instant"  # Fast model for UX
    
    def generate_response(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> str:
        """
        Generate a single short response.
        Input: Plain text prompt
        Output: ONE short response only
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content.strip()
            return content
        
        except Exception as e:
            print(f"Error in Groq generation: {e}")
            # Return fallback response
            return prompt  # Return original if generation fails
    
    def rephrase_question(self, question: str, context: Optional[str] = None) -> str:
        """
        Rephrase a system-generated question to be more natural.
        Adds light empathy but preserves the question's intent.
        Returns EXACTLY ONE sentence.
        """
        prompt = f"""You are rephrasing a system-generated question for an HR chatbot.

Rules:
- Return EXACTLY ONE sentence
- Ask EXACTLY ONE question
- Do NOT provide multiple options
- Do NOT explain
- Do NOT add prefixes like "Here are some options"
- Keep it short and professional
- Just return the rephrased question, nothing else

Input question: {question}"""
        
        if context:
            prompt += f"\n\nContext: {context}"
        
        prompt += "\n\nOutput (one sentence only):"
        
        response = self.generate_response(prompt, max_tokens=50, temperature=0.5)
        
        # Clean up response
        response = response.strip()
        
        # Remove quotes if present
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        if response.startswith("'") and response.endswith("'"):
            response = response[1:-1]
        
        # Remove numbering like "1. " or "1)" at the start
        import re
        response = re.sub(r'^\d+[\.\)]\s*', '', response)
        
        # Take only first sentence
        sentences = re.split(r'[.!?]+', response)
        if sentences:
            response = sentences[0].strip()
            if not response.endswith(('.', '!', '?')):
                response += '?'
        
        return response if response else question
    
    def generate_empathy(self, situation: str) -> str:
        """
        Generate empathetic response for general HR conversation.
        """
        prompt = f"As an HR assistant, provide a brief, empathetic response to: {situation}"
        return self.generate_response(prompt, max_tokens=100, temperature=0.7)
    
    def generate_conversational_response(self, user_message: str, context: Optional[str] = None) -> str:
        """
        Generate conversational response for general HR chat.
        Uses a comprehensive system prompt for professional HR assistance.
        """
        system_prompt = """You are a professional, knowledgeable, and empathetic HR assistant for a company. Your role is to help employees with HR-related questions and concerns.

Your capabilities:
- Answer questions about company policies, benefits, leave policies, and HR procedures
- Provide information about employee benefits, health insurance, retirement plans
- Help with general HR inquiries about onboarding, offboarding, performance reviews
- Offer guidance on workplace policies, code of conduct, and professional development
- Provide empathetic support for workplace concerns
- Direct employees to appropriate resources when needed

Your communication style:
- Professional yet warm and approachable
- Clear, concise, and easy to understand
- Empathetic when dealing with sensitive topics
- Honest about what you know and don't know
- Always maintain confidentiality and professionalism
- If you don't know something, admit it and suggest they contact HR directly

Important rules:
- NEVER make up or guess information about company policies
- NEVER provide medical, legal, or financial advice
- NEVER promise specific outcomes or guarantees
- If asked about something you're unsure of, suggest contacting HR directly
- Keep responses SHORT and CONCISE (1-2 sentences maximum, only expand if absolutely necessary)
- Be direct and to the point - no unnecessary explanations
- Always be helpful and supportive

Now respond to the employee's message:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if context:
            messages.append({"role": "system", "content": f"Additional context: {context}"})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=100,  # Reduced for shorter responses
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error in Groq conversational response: {e}")
            return "I'm here to help with your HR questions. Could you please rephrase your question?"

