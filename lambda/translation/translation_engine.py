"""
AI-powered code translation engine that coordinates all translation components.

This module provides a high-level interface for the complete translation workflow,
integrating language detection, AI-powered translation, and quality assurance.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from .base_translator import CodeTranslator, TranslatorFactory, TranslationError
from .language_detector import LanguageDetector
from .models import TranslationRequest, TranslationResult
from .quality_assurance import TranslationQualityAssurance

logger = logging.getLogger(__name__)


@dataclass
class TranslationEngineConfig:
    """Configuration for the translation engine."""
    translator_type: str = "bedrock"
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    region_name: str = "us-east-1"
    target_language: str = "python"
    enable_quality_assurance: bool = True
    enable_code_optimization: bool = True
    max_file_size_mb: int = 10
    translation_timeout: float = 120.0


class TranslationEngine:
    """
    AI-powered code translation engine.
    
    This class provides a complete translation workflow that includes:
    - Automatic language detection
    - AI-powered code translation using Bedrock
    - Translation quality assurance and validation
    - Code optimization for Python best practices
    """
    
    def __init__(self, config: Optional[TranslationEngineConfig] = None):
        """
        Initialize the translation engine.
        
        Args:
            config: Configuration for the translation engine
        """
        self.config = config or TranslationEngineConfig()
        
        # Initialize components
        self.language_detector = LanguageDetector()
        self.quality_assurance = TranslationQualityAssurance()
        
        # Initialize translator
        self.translator = self._create_translator()
        
        logger.info(f"Translation engine initialized with {self.config.translator_type} translator")
    
    def _create_translator(self) -> CodeTranslator:
        """Create and configure the translator instance."""
        try:
            translator_kwargs = {
                'target_language': self.config.target_language
            }
            
            # Add Bedrock-specific configuration
            if self.config.translator_type == 'bedrock':
                translator_kwargs.update({
                    'model_id': self.config.model_id,
                    'region_name': self.config.region_name
                })
            
            translator = TranslatorFactory.create_translator(
                self.config.translator_type,
                **translator_kwargs
            )
            
            # Set timeout
            translator.set_timeout(self.config.translation_timeout)
            
            return translator
            
        except Exception as e:
            logger.error(f"Failed to create translator: {str(e)}")
            raise TranslationError(
                f"Failed to initialize translator: {str(e)}",
                error_code="TRANSLATOR_INIT_ERROR",
                original_error=e
            )
    
    def translate_code(self, 
                      code_content: str,
                      file_path: str,
                      source_language: Optional[str] = None) -> TranslationResult:
        """
        Translate code from any supported language to Python.
        
        Args:
            code_content: Source code to translate
            file_path: Path to the source file (used for language detection)
            source_language: Source language (if known, otherwise auto-detected)
            
        Returns:
            TranslationResult: Complete translation result with metadata
            
        Raises:
            TranslationError: If translation fails
        """
        start_time = time.time()
        
        try:
            # Validate input
            self._validate_input(code_content, file_path)
            
            # Detect language if not provided
            if source_language is None:
                source_language = self.language_detector.detect_language(file_path, code_content)
                logger.info(f"Detected language: {source_language}")
            
            # Check if translation is needed
            if source_language.lower() == 'python':
                return self._create_passthrough_result(code_content, file_path, start_time)
            
            # Validate language support
            if not self.translator.is_supported_language(source_language):
                supported_languages = self.translator.get_supported_languages()
                raise TranslationError(
                    f"Language '{source_language}' is not supported. Supported languages: {supported_languages}",
                    error_code="UNSUPPORTED_LANGUAGE"
                )
            
            # Create translation request
            request = TranslationRequest(
                source_code=code_content,
                source_language=source_language,
                target_language=self.config.target_language,
                file_path=file_path,
                original_size=len(code_content.encode('utf-8'))
            )
            
            # Perform translation
            logger.info(f"Starting translation from {source_language} to {self.config.target_language}")
            result = self.translator.translate(request)
            
            # Apply quality assurance if enabled
            if self.config.enable_quality_assurance and result.translation_success:
                result = self._apply_quality_assurance(result, code_content, source_language)
            
            # Apply code optimization if enabled
            if self.config.enable_code_optimization and result.translation_success:
                result = self._apply_code_optimization(result)
            
            # Add engine metadata
            result.add_metadata("translation_engine_version", "1.0.0")
            result.add_metadata("engine_config", {
                "translator_type": self.config.translator_type,
                "model_id": self.config.model_id,
                "quality_assurance_enabled": self.config.enable_quality_assurance,
                "code_optimization_enabled": self.config.enable_code_optimization
            })
            
            total_time = time.time() - start_time
            result.add_metadata("total_processing_time", total_time)
            
            logger.info(f"Translation completed in {total_time:.2f}s with confidence {result.confidence_score:.2f}")
            
            return result
            
        except TranslationError:
            # Re-raise translation errors as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error in translation engine: {str(e)}")
            raise TranslationError(
                f"Translation engine error: {str(e)}",
                error_code="ENGINE_ERROR",
                original_error=e
            )
    
    def translate_multiple_files(self, 
                               files: List[Dict[str, str]]) -> List[TranslationResult]:
        """
        Translate multiple files in batch.
        
        Args:
            files: List of dictionaries with 'content', 'path', and optionally 'language' keys
            
        Returns:
            List[TranslationResult]: Results for each file
        """
        results = []
        
        for i, file_info in enumerate(files):
            try:
                content = file_info['content']
                path = file_info['path']
                language = file_info.get('language')
                
                logger.info(f"Translating file {i+1}/{len(files)}: {path}")
                
                result = self.translate_code(content, path, language)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to translate file {path}: {str(e)}")
                
                # Create error result
                error_result = TranslationResult(
                    translated_code="",
                    source_language=file_info.get('language', 'unknown'),
                    translation_success=False,
                    translation_time=0.0,
                    target_language=self.config.target_language,
                    original_size=len(file_info['content'].encode('utf-8')),
                    confidence_score=0.0,
                    error_message=str(e)
                )
                results.append(error_result)
        
        return results
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported source languages.
        
        Returns:
            List[str]: List of supported language names
        """
        return self.translator.get_supported_languages()
    
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Get information about the translation engine configuration.
        
        Returns:
            Dict[str, Any]: Engine configuration and capabilities
        """
        return {
            "translator_type": self.config.translator_type,
            "model_id": self.config.model_id,
            "target_language": self.config.target_language,
            "supported_languages": self.get_supported_languages(),
            "quality_assurance_enabled": self.config.enable_quality_assurance,
            "code_optimization_enabled": self.config.enable_code_optimization,
            "max_file_size_mb": self.config.max_file_size_mb,
            "translation_timeout": self.config.translation_timeout
        }
    
    def _validate_input(self, code_content: str, file_path: str) -> None:
        """Validate input parameters."""
        if not code_content or not code_content.strip():
            raise TranslationError("Code content cannot be empty", error_code="EMPTY_CODE")
        
        if not file_path:
            raise TranslationError("File path must be provided", error_code="MISSING_FILE_PATH")
        
        # Check file size
        content_size_mb = len(code_content.encode('utf-8')) / (1024 * 1024)
        if content_size_mb > self.config.max_file_size_mb:
            raise TranslationError(
                f"File size ({content_size_mb:.1f}MB) exceeds maximum allowed size ({self.config.max_file_size_mb}MB)",
                error_code="FILE_TOO_LARGE"
            )
    
    def _create_passthrough_result(self, 
                                 code_content: str, 
                                 file_path: str, 
                                 start_time: float) -> TranslationResult:
        """Create a result for Python files that don't need translation."""
        result = TranslationResult(
            translated_code=code_content,
            source_language="python",
            translation_success=True,
            translation_time=time.time() - start_time,
            target_language=self.config.target_language,
            original_size=len(code_content.encode('utf-8')),
            confidence_score=1.0
        )
        
        result.add_metadata("translation_type", "passthrough")
        result.add_metadata("reason", "Source is already Python")
        result.add_warning("No translation needed - source is already Python")
        
        logger.info(f"Python file passed through without translation: {file_path}")
        
        return result
    
    def _apply_quality_assurance(self, 
                               result: TranslationResult,
                               original_code: str,
                               source_language: str) -> TranslationResult:
        """Apply quality assurance to the translation result."""
        try:
            logger.debug("Applying quality assurance to translation")
            
            # Assess translation quality
            quality_metrics = self.quality_assurance.assess_translation_quality(
                original_code,
                result.translated_code,
                source_language
            )
            
            # Update result with quality metrics
            result.add_metadata("quality_metrics", quality_metrics.to_dict())
            
            # Add quality issues as warnings
            for issue in quality_metrics.issues:
                result.add_warning(f"Quality issue: {issue}")
            
            # Add improvement suggestions
            for suggestion in quality_metrics.suggestions:
                result.add_metadata("improvement_suggestion", suggestion)
            
            # Update confidence score based on quality
            if hasattr(quality_metrics, 'overall_score'):
                # Combine original confidence with quality score
                combined_confidence = (result.confidence_score + quality_metrics.overall_score) / 2
                result.confidence_score = combined_confidence
            
            logger.debug(f"Quality assurance completed. Overall score: {quality_metrics.overall_score:.2f}")
            
        except Exception as e:
            logger.warning(f"Quality assurance failed: {str(e)}")
            result.add_warning(f"Quality assurance error: {str(e)}")
        
        return result
    
    def _apply_code_optimization(self, result: TranslationResult) -> TranslationResult:
        """Apply code optimization to the translated Python code."""
        try:
            logger.debug("Applying code optimization")
            
            optimized_code, optimizations = self.quality_assurance.optimize_translated_code(
                result.translated_code
            )
            
            if optimized_code and optimizations:
                # Update the translated code with optimized version
                result.translated_code = optimized_code
                result.add_metadata("optimizations_applied", optimizations)
                
                logger.debug(f"Applied {len(optimizations)} code optimizations")
                
                # Add optimization info as metadata
                for optimization in optimizations:
                    result.add_metadata("optimization", optimization)
            else:
                result.add_metadata("optimization_result", "No optimizations applied")
            
        except Exception as e:
            logger.warning(f"Code optimization failed: {str(e)}")
            result.add_warning(f"Code optimization error: {str(e)}")
        
        return result


# Convenience functions for easy usage

def create_translation_engine(translator_type: str = "bedrock", **kwargs) -> TranslationEngine:
    """
    Create a translation engine with the specified configuration.
    
    Args:
        translator_type: Type of translator to use ('bedrock' or 'mock')
        **kwargs: Additional configuration parameters
        
    Returns:
        TranslationEngine: Configured translation engine
    """
    config = TranslationEngineConfig(translator_type=translator_type, **kwargs)
    return TranslationEngine(config)


def translate_code_file(file_path: str, 
                       code_content: str,
                       translator_type: str = "bedrock",
                       **kwargs) -> TranslationResult:
    """
    Translate a single code file using the default configuration.
    
    Args:
        file_path: Path to the source file
        code_content: Source code content
        translator_type: Type of translator to use
        **kwargs: Additional configuration parameters
        
    Returns:
        TranslationResult: Translation result
    """
    engine = create_translation_engine(translator_type, **kwargs)
    return engine.translate_code(code_content, file_path)


def get_supported_languages(translator_type: str = "bedrock") -> List[str]:
    """
    Get list of supported languages for translation.
    
    Args:
        translator_type: Type of translator to query
        
    Returns:
        List[str]: List of supported language names
    """
    engine = create_translation_engine(translator_type)
    return engine.get_supported_languages()