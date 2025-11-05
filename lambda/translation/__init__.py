"""
Translation module for code translation and compilation functionality.

This module provides the core infrastructure for translating code from various
programming languages to Python, including language detection, translation
interfaces, and data models.
"""

from .language_detector import LanguageDetector
from .base_translator import (
    CodeTranslator,
    TranslationError,
    UnsupportedLanguageError,
    TranslationTimeoutError,
    MockTranslator,
    TranslatorFactory
)
from .bedrock_translator import BedrockTranslator
from .quality_assurance import TranslationQualityAssurance, QualityMetrics
from .models import (
    TranslationRequest,
    TranslationResult,
    CompilationResult,
    ProcessingOutput
)
from .translation_engine import (
    TranslationEngine,
    TranslationEngineConfig,
    create_translation_engine,
    translate_code_file
)

from .intelligent_orchestrator import (
    IntelligentTranslationOrchestrator,
    OrchestrationResult,
    process_code_translation_intelligent
)


__all__ = [
    # Language Detection
    'LanguageDetector',
    
    # Translation Classes
    'CodeTranslator',
    'MockTranslator',
    'BedrockTranslator',
    'TranslatorFactory',
    
    # Translation Engine
    'TranslationEngine',
    'TranslationEngineConfig',
    'create_translation_engine',
    'translate_code_file',
    

    
    # Intelligent Orchestration
    'IntelligentTranslationOrchestrator',
    'OrchestrationResult',
    'process_code_translation_intelligent',
    

    
    # Quality Assurance
    'TranslationQualityAssurance',
    'QualityMetrics',
    
    # Exception Classes
    'TranslationError',
    'UnsupportedLanguageError',
    'TranslationTimeoutError',
    
    # Data Models
    'TranslationRequest',
    'TranslationResult',
    'CompilationResult',
    'ProcessingOutput',
]

# Version information
__version__ = '1.0.0'

# Module-level convenience functions
def create_language_detector() -> LanguageDetector:
    """
    Create a new LanguageDetector instance.
    
    Returns:
        LanguageDetector: Configured language detector
    """
    return LanguageDetector()

def create_mock_translator() -> MockTranslator:
    """
    Create a new MockTranslator instance for testing.
    
    Returns:
        MockTranslator: Mock translator for testing
    """
    return MockTranslator()

def get_supported_languages() -> list[str]:
    """
    Get list of all supported programming languages.
    
    Returns:
        list[str]: List of supported language names
    """
    detector = LanguageDetector()
    return detector.get_supported_languages()

def create_bedrock_translator(**kwargs) -> BedrockTranslator:
    """
    Create a new BedrockTranslator instance.
    
    Args:
        **kwargs: Configuration parameters for the translator
        
    Returns:
        BedrockTranslator: Configured Bedrock translator
    """
    return BedrockTranslator(**kwargs)

# Register available translators
TranslatorFactory.register_translator('bedrock', BedrockTranslator)