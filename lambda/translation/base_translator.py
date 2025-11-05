"""
Base translator classes and interfaces for code translation workflow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging
import time
from datetime import datetime

from .models import TranslationRequest, TranslationResult

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Base exception for translation errors."""
    
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        self.timestamp = datetime.now()


class UnsupportedLanguageError(TranslationError):
    """Raised when attempting to translate from an unsupported language."""
    
    def __init__(self, language: str):
        super().__init__(
            f"Language '{language}' is not supported for translation",
            error_code="UNSUPPORTED_LANGUAGE"
        )
        self.language = language


class TranslationTimeoutError(TranslationError):
    """Raised when translation operation times out."""
    
    def __init__(self, timeout_seconds: float):
        super().__init__(
            f"Translation operation timed out after {timeout_seconds} seconds",
            error_code="TRANSLATION_TIMEOUT"
        )
        self.timeout_seconds = timeout_seconds


class CodeTranslator(ABC):
    """
    Abstract base class for code translators.
    
    Defines the interface that all concrete translator implementations must follow.
    """
    
    def __init__(self, target_language: str = "python"):
        """
        Initialize the translator.
        
        Args:
            target_language: The target language for translation (default: python)
        """
        self.target_language = target_language
        self.supported_source_languages = self._get_supported_languages()
        self.translation_timeout = 120.0  # Default timeout in seconds
        
    @abstractmethod
    def _get_supported_languages(self) -> List[str]:
        """
        Get list of supported source languages.
        
        Returns:
            List[str]: List of supported language names
        """
        pass
    
    @abstractmethod
    def _translate_code(self, request: TranslationRequest) -> TranslationResult:
        """
        Perform the actual code translation.
        
        Args:
            request: Translation request containing source code and metadata
            
        Returns:
            TranslationResult: Result of the translation operation
            
        Raises:
            TranslationError: If translation fails
        """
        pass
    
    def translate(self, request: TranslationRequest) -> TranslationResult:
        """
        Translate source code to the target language.
        
        Args:
            request: Translation request containing source code and metadata
            
        Returns:
            TranslationResult: Result of the translation operation
        """
        start_time = time.time()
        
        try:
            # Validate request
            self._validate_request(request)
            
            # Log translation start
            logger.info(f"Starting translation from {request.source_language} to {self.target_language}")
            logger.debug(f"File: {request.file_path}, Size: {request.original_size} bytes")
            
            # Perform translation
            result = self._translate_code(request)
            
            # Update timing information
            result.translation_time = time.time() - start_time
            
            # Log completion
            if result.translation_success:
                logger.info(f"Translation completed successfully in {result.translation_time:.2f}s")
            else:
                logger.warning(f"Translation failed after {result.translation_time:.2f}s: {result.error_message}")
            
            return result
            
        except TranslationError:
            # Re-raise translation errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            translation_time = time.time() - start_time
            logger.error(f"Unexpected error during translation: {str(e)}")
            
            raise TranslationError(
                f"Unexpected error during translation: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                original_error=e
            )
    
    def _validate_request(self, request: TranslationRequest) -> None:
        """
        Validate the translation request.
        
        Args:
            request: Translation request to validate
            
        Raises:
            TranslationError: If request is invalid
        """
        if not request.source_code or not request.source_code.strip():
            raise TranslationError("Source code cannot be empty", error_code="EMPTY_SOURCE_CODE")
        
        if not request.source_language:
            raise TranslationError("Source language must be specified", error_code="MISSING_SOURCE_LANGUAGE")
        
        if request.source_language not in self.supported_source_languages:
            raise UnsupportedLanguageError(request.source_language)
        
        if request.target_language != self.target_language:
            raise TranslationError(
                f"Target language '{request.target_language}' does not match translator target '{self.target_language}'",
                error_code="TARGET_LANGUAGE_MISMATCH"
            )
        
        # Check for reasonable size limits
        max_size = 10 * 1024 * 1024  # 10MB
        if request.original_size > max_size:
            raise TranslationError(
                f"Source code size ({request.original_size} bytes) exceeds maximum allowed size ({max_size} bytes)",
                error_code="SOURCE_TOO_LARGE"
            )
    
    def is_supported_language(self, language: str) -> bool:
        """
        Check if a source language is supported.
        
        Args:
            language: Language name to check
            
        Returns:
            bool: True if language is supported
        """
        return language in self.supported_source_languages
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported source languages.
        
        Returns:
            List[str]: List of supported language names
        """
        return self.supported_source_languages.copy()
    
    def set_timeout(self, timeout_seconds: float) -> None:
        """
        Set the translation timeout.
        
        Args:
            timeout_seconds: Timeout in seconds
        """
        if timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        
        self.translation_timeout = timeout_seconds
        logger.debug(f"Translation timeout set to {timeout_seconds} seconds")


class MockTranslator(CodeTranslator):
    """
    Mock translator for testing purposes.
    
    This translator doesn't perform actual translation but provides a working
    implementation for testing the translation workflow.
    """
    
    def _get_supported_languages(self) -> List[str]:
        """Get list of supported source languages."""
        return ['javascript', 'typescript', 'java', 'csharp', 'cpp', 'go', 'rust']
    
    def _translate_code(self, request: TranslationRequest) -> TranslationResult:
        """
        Perform mock translation by wrapping source code in Python comments.
        
        Args:
            request: Translation request
            
        Returns:
            TranslationResult: Mock translation result
        """
        # Create a simple mock translation
        translated_code = f'''"""
Translated from {request.source_language} to Python
Original file: {request.file_path}
Translation performed by MockTranslator
"""

# Original {request.source_language} code:
{self._comment_out_code(request.source_code, request.source_language)}

# Mock Python equivalent:
def main():
    print("This is a mock translation from {request.source_language}")
    print("Original code has been commented out above")
    return "Mock translation completed"

if __name__ == "__main__":
    result = main()
    print(result)
'''
        
        # Create result
        result = TranslationResult(
            translated_code=translated_code,
            source_language=request.source_language,
            translation_success=True,
            translation_time=0.0,  # Will be set by parent class
            target_language=self.target_language,
            original_size=request.original_size,
            confidence_score=0.8  # Mock confidence
        )
        
        # Add some mock metadata
        result.add_metadata("translator_type", "mock")
        result.add_metadata("translation_method", "comment_wrapping")
        result.add_warning("This is a mock translation for testing purposes")
        
        return result
    
    def _comment_out_code(self, code: str, language: str) -> str:
        """
        Comment out the original code based on the source language.
        
        Args:
            code: Original source code
            language: Source language
            
        Returns:
            str: Code with each line commented out
        """
        lines = code.split('\n')
        commented_lines = []
        
        for line in lines:
            if line.strip():  # Only comment non-empty lines
                commented_lines.append(f"# {line}")
            else:
                commented_lines.append("#")
        
        return '\n'.join(commented_lines)


class TranslatorFactory:
    """
    Factory class for creating translator instances.
    """
    
    _translators: Dict[str, type] = {
        'mock': MockTranslator,
        # Additional translator types can be registered here
    }
    
    @classmethod
    def _register_bedrock_translator(cls):
        """Register BedrockTranslator if available."""
        try:
            from .bedrock_translator import BedrockTranslator
            cls._translators['bedrock'] = BedrockTranslator
        except ImportError:
            # BedrockTranslator not available (e.g., in development without boto3)
            pass
    
    @classmethod
    def create_translator(cls, translator_type: str, **kwargs) -> CodeTranslator:
        """
        Create a translator instance.
        
        Args:
            translator_type: Type of translator to create
            **kwargs: Additional arguments for translator initialization
            
        Returns:
            CodeTranslator: Translator instance
            
        Raises:
            ValueError: If translator type is not supported
        """
        # Register BedrockTranslator if not already registered
        if 'bedrock' not in cls._translators:
            cls._register_bedrock_translator()
        
        if translator_type not in cls._translators:
            available_types = list(cls._translators.keys())
            raise ValueError(f"Unsupported translator type '{translator_type}'. Available types: {available_types}")
        
        translator_class = cls._translators[translator_type]
        return translator_class(**kwargs)
    
    @classmethod
    def register_translator(cls, translator_type: str, translator_class: type) -> None:
        """
        Register a new translator type.
        
        Args:
            translator_type: Name for the translator type
            translator_class: Translator class (must inherit from CodeTranslator)
        """
        if not issubclass(translator_class, CodeTranslator):
            raise ValueError("Translator class must inherit from CodeTranslator")
        
        cls._translators[translator_type] = translator_class
        logger.info(f"Registered translator type: {translator_type}")
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """
        Get list of available translator types.
        
        Returns:
            List[str]: List of available translator type names
        """
        return list(cls._translators.keys())