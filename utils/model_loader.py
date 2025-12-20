"""
Model pre-loader for HR Conversational Agent.
Pre-loads all models before server starts to avoid slow first responses.
"""

from typing import Optional
from intent.intent_router import IntentRouter
from slots.slot_selector import SlotSelector
from slots.slot_extractor import SlotExtractor
from llm.groq_client import GroqClient


class ModelLoader:
    """Pre-loads all models for faster response times."""
    
    def __init__(self):
        """Initialize model loader."""
        self.intent_router: Optional[IntentRouter] = None
        self.slot_selector: Optional[SlotSelector] = None
        self.slot_extractor: Optional[SlotExtractor] = None
        self.groq_client: Optional[GroqClient] = None
        self.models_loaded = False
    
    def load_all_models(self) -> bool:
        """
        Pre-load all models.
        Returns True if all models loaded successfully, False otherwise.
        """
        print("\n" + "=" * 60)
        print("PRE-LOADING ALL MODELS")
        print("=" * 60)
        
        try:
            # Load Groq client first (needed for intent detection)
            print("\n[1/4] Loading Groq client...")
            self.groq_client = GroqClient()
            print("✓ Groq client loaded")
            
            # Load intent router (uses Groq)
            print("\n[2/4] Loading Intent Router (Groq-based)...")
            self.intent_router = IntentRouter(groq_client=self.groq_client)
            print("✓ Intent Router loaded")
            
            # Load slot selector
            print("\n[3/4] Loading Slot Selector (ELECTRA-small)...")
            self.slot_selector = SlotSelector()
            print("✓ Slot Selector loaded")
            
            # Load slot extractor
            print("\n[4/4] Loading Slot Extractor (MobileBERT-SQuAD2)...")
            self.slot_extractor = SlotExtractor()
            print("✓ Slot Extractor loaded")
            
            self.models_loaded = True
            print("\n" + "=" * 60)
            print("✓ ALL MODELS LOADED SUCCESSFULLY")
            print("=" * 60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error loading models: {e}")
            print("Some models may not be available. System will use fallbacks.\n")
            return False
    
    def get_components(self):
        """Get pre-loaded components."""
        return {
            'intent_router': self.intent_router,
            'slot_selector': self.slot_selector,
            'slot_extractor': self.slot_extractor,
            'groq_client': self.groq_client
        }


# Global model loader instance
_model_loader = None


def get_model_loader() -> ModelLoader:
    """Get or create global model loader instance."""
    global _model_loader
    if _model_loader is None:
        _model_loader = ModelLoader()
    return _model_loader


def preload_models() -> bool:
    """Pre-load all models. Call this before starting the server."""
    loader = get_model_loader()
    return loader.load_all_models()

