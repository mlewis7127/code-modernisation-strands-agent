"""
Translation module for intelligent code translation using AI agents.

This module provides the intelligent orchestrator that uses specialized AI agents
to translate code from various programming languages to Python using a design-driven
approach.
"""

from .language_detector import LanguageDetector
from .models import (
    CompilationResult,
    ProcessingOutput
)
from .intelligent_orchestrator import (
    IntelligentTranslationOrchestrator,
    OrchestrationResult,
    process_code_translation_intelligent
)


__all__ = [
    # Language Detection
    'LanguageDetector',
    
    # Intelligent Orchestration
    'IntelligentTranslationOrchestrator',
    'OrchestrationResult',
    'process_code_translation_intelligent',
    
    # Data Models
    'CompilationResult',
    'ProcessingOutput',
]

# Version information
__version__ = '2.0.0'

# Module-level convenience functions
def create_language_detector() -> LanguageDetector:
    """
    Create a new LanguageDetector instance.
    
    Returns:
        LanguageDetector: Configured language detector
    """
    return LanguageDetector()

def get_supported_languages() -> list[str]:
    """
    Get list of all supported programming languages.
    
    Returns:
        list[str]: List of supported language names
    """
    detector = LanguageDetector()
    return detector.get_supported_languages()