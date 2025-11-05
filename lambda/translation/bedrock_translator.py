"""
Bedrock-based code translator for AI-powered language conversion.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    # boto3 not available - this is expected in development environments
    BOTO3_AVAILABLE = False
    ClientError = Exception
    BotoCoreError = Exception

from .base_translator import CodeTranslator, TranslationError, TranslationTimeoutError
from .models import TranslationRequest, TranslationResult
from .quality_assurance import TranslationQualityAssurance

logger = logging.getLogger(__name__)


class BedrockTranslator(CodeTranslator):
    """
    AI-powered code translator using AWS Bedrock for language conversion.
    
    This translator uses Bedrock's language models to translate code from various
    programming languages to Python while preserving functionality and structure.
    """
    
    def __init__(self, 
                 model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
                 region_name: str = "us-east-1",
                 target_language: str = "python"):
        """
        Initialize the Bedrock translator.
        
        Args:
            model_id: Bedrock model ID to use for translation
            region_name: AWS region for Bedrock service
            target_language: Target language for translation (default: python)
        """
        super().__init__(target_language)
        
        self.model_id = model_id
        self.region_name = region_name
        
        # Initialize Bedrock client
        if not BOTO3_AVAILABLE:
            raise TranslationError(
                "boto3 is not available - BedrockTranslator requires AWS SDK",
                error_code="BOTO3_NOT_AVAILABLE"
            )
        
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=region_name
            )
            logger.info(f"Initialized Bedrock client for region {region_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise TranslationError(
                f"Failed to initialize Bedrock client: {str(e)}",
                error_code="BEDROCK_INIT_ERROR",
                original_error=e
            )
        
        # Load translation prompts
        self.translation_prompts = self._load_translation_prompts()
        
        # Initialize quality assurance
        self.quality_assurance = TranslationQualityAssurance()
        
        # Translation settings
        self.max_tokens = 4000
        self.temperature = 0.1  # Low temperature for consistent code translation
        
    def _get_supported_languages(self) -> List[str]:
        """Get list of supported source languages."""
        return [
            'javascript', 'typescript', 'java', 'csharp', 'cpp', 'go', 'rust'
        ]
    
    def _load_translation_prompts(self) -> Dict[str, str]:
        """
        Load language-specific translation prompts.
        
        Returns:
            Dict[str, str]: Mapping of language to translation prompt
        """
        return {
            'javascript': self._get_javascript_prompt(),
            'typescript': self._get_typescript_prompt(),
            'java': self._get_java_prompt(),
            'csharp': self._get_csharp_prompt(),
            'cpp': self._get_cpp_prompt(),
            'go': self._get_go_prompt(),
            'rust': self._get_rust_prompt()
        }
    
    def _get_javascript_prompt(self) -> str:
        """Get JavaScript to Python translation prompt."""
        return """You are an expert code translator. Translate the following JavaScript code to Python while preserving all functionality, logic, and behavior.

Guidelines:
1. Convert JavaScript syntax to equivalent Python syntax
2. Map JavaScript libraries to Python equivalents (e.g., fetch -> requests, setTimeout -> time.sleep)
3. Handle async/await patterns using Python asyncio when appropriate
4. Convert JavaScript objects to Python dictionaries or classes as appropriate
5. Preserve all comments and documentation
6. Ensure the translated code is readable and follows Python best practices
7. Handle JavaScript-specific features like closures, prototypes, and hoisting appropriately
8. Convert ES6+ features to Python equivalents

Input JavaScript code:
{source_code}

Provide only the translated Python code without explanations or markdown formatting."""
    
    def _get_typescript_prompt(self) -> str:
        """Get TypeScript to Python translation prompt."""
        return """You are an expert code translator. Translate the following TypeScript code to Python while preserving all functionality, logic, and behavior.

Guidelines:
1. Convert TypeScript syntax to equivalent Python syntax
2. Map TypeScript types to Python type hints where appropriate
3. Handle interfaces and type definitions using Python typing module
4. Convert TypeScript classes to Python classes with proper inheritance
5. Map TypeScript libraries to Python equivalents
6. Preserve all comments and documentation
7. Handle generics using Python typing.Generic
8. Convert decorators and metadata appropriately
9. Ensure the translated code is readable and follows Python best practices

Input TypeScript code:
{source_code}

Provide only the translated Python code without explanations or markdown formatting."""
    
    def _get_java_prompt(self) -> str:
        """Get Java to Python translation prompt."""
        return """You are an expert code translator. Translate the following Java code to Python while preserving all functionality, logic, and behavior.

Guidelines:
1. Convert Java syntax to equivalent Python syntax
2. Map Java classes to Python classes with appropriate inheritance
3. Handle Java interfaces using Python abstract base classes
4. Convert Java collections to Python equivalents (List, Dict, Set)
5. Map Java libraries to Python equivalents where possible
6. Handle Java access modifiers using Python conventions (private with underscore)
7. Convert Java exceptions to Python exceptions
8. Preserve all comments and documentation
9. Handle Java generics using Python typing
10. Convert static methods and variables appropriately

Input Java code:
{source_code}

Provide only the translated Python code without explanations or markdown formatting."""
    
    def _get_csharp_prompt(self) -> str:
        """Get C# to Python translation prompt."""
        return """You are an expert code translator. Translate the following C# code to Python while preserving all functionality, logic, and behavior.

Guidelines:
1. Convert C# syntax to equivalent Python syntax
2. Map C# classes to Python classes with appropriate inheritance
3. Handle C# interfaces using Python abstract base classes
4. Convert C# collections to Python equivalents (List, Dict, Set)
5. Map .NET libraries to Python equivalents where possible
6. Handle C# properties using Python @property decorators
7. Convert C# LINQ to Python list comprehensions or filter/map operations
8. Preserve all comments and documentation
9. Handle C# generics using Python typing
10. Convert async/await patterns to Python asyncio

Input C# code:
{source_code}

Provide only the translated Python code without explanations or markdown formatting."""
    
    def _get_cpp_prompt(self) -> str:
        """Get C++ to Python translation prompt."""
        return """You are an expert code translator. Translate the following C++ code to Python while preserving all functionality, logic, and behavior.

Guidelines:
1. Convert C++ syntax to equivalent Python syntax
2. Handle C++ classes and inheritance in Python
3. Convert C++ pointers and references to Python object references
4. Map C++ STL containers to Python equivalents (list, dict, set)
5. Handle C++ templates using Python generics where appropriate
6. Convert C++ memory management to Python's automatic memory management
7. Map C++ algorithms to Python equivalents or use appropriate libraries
8. Preserve all comments and documentation
9. Handle C++ namespaces using Python modules/classes
10. Convert operator overloading to Python magic methods

Input C++ code:
{source_code}

Provide only the translated Python code without explanations or markdown formatting."""
    
    def _get_go_prompt(self) -> str:
        """Get Go to Python translation prompt."""
        return """You are an expert code translator. Translate the following Go code to Python while preserving all functionality, logic, and behavior.

Guidelines:
1. Convert Go syntax to equivalent Python syntax
2. Map Go structs to Python classes or dataclasses
3. Handle Go interfaces using Python abstract base classes
4. Convert Go goroutines to Python asyncio tasks
5. Map Go channels to Python asyncio queues or similar constructs
6. Handle Go error handling using Python exceptions
7. Convert Go packages to Python modules
8. Preserve all comments and documentation
9. Map Go standard library to Python equivalents
10. Handle Go's defer statements using Python context managers or try/finally

Input Go code:
{source_code}

Provide only the translated Python code without explanations or markdown formatting."""
    
    def _get_rust_prompt(self) -> str:
        """Get Rust to Python translation prompt."""
        return """You are an expert code translator. Translate the following Rust code to Python while preserving all functionality, logic, and behavior.

Guidelines:
1. Convert Rust syntax to equivalent Python syntax
2. Map Rust structs and enums to Python classes or dataclasses
3. Handle Rust traits using Python abstract base classes
4. Convert Rust ownership and borrowing to Python object references
5. Map Rust Result and Option types to Python equivalents or exception handling
6. Handle Rust pattern matching using Python match statements (3.10+) or if/elif
7. Convert Rust macros to Python functions or decorators where appropriate
8. Preserve all comments and documentation
9. Map Rust standard library to Python equivalents
10. Handle Rust's memory safety features using Python's automatic memory management

Input Rust code:
{source_code}

Provide only the translated Python code without explanations or markdown formatting."""
    
    def _translate_code(self, request: TranslationRequest) -> TranslationResult:
        """
        Perform the actual code translation using Bedrock.
        
        Args:
            request: Translation request containing source code and metadata
            
        Returns:
            TranslationResult: Result of the translation operation
        """
        start_time = time.time()
        
        try:
            # Get language-specific prompt
            if request.source_language not in self.translation_prompts:
                raise TranslationError(
                    f"No translation prompt available for language: {request.source_language}",
                    error_code="NO_PROMPT_AVAILABLE"
                )
            
            prompt_template = self.translation_prompts[request.source_language]
            prompt = prompt_template.format(source_code=request.source_code)
            
            # Prepare Bedrock request
            bedrock_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            logger.debug(f"Calling Bedrock model {self.model_id} for {request.source_language} translation")
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(bedrock_request),
                contentType='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'content' not in response_body or not response_body['content']:
                raise TranslationError(
                    "Empty response from Bedrock model",
                    error_code="EMPTY_BEDROCK_RESPONSE"
                )
            
            translated_code = response_body['content'][0]['text'].strip()
            
            # Assess translation quality
            quality_metrics = self.quality_assurance.assess_translation_quality(
                request.source_code,
                translated_code,
                request.source_language
            )
            
            # Optimize the translated code
            optimized_code, optimizations = self.quality_assurance.optimize_translated_code(translated_code)
            
            # Use optimized code if optimization was successful
            if optimized_code and optimizations:
                translated_code = optimized_code
                logger.info(f"Applied {len(optimizations)} code optimizations:")
                for i, optimization in enumerate(optimizations, 1):
                    logger.info(f"  {i}. {optimization}")
            
            # Validate translation result (legacy validation for compatibility)
            validation_result = self._validate_translation(
                request.source_code, 
                translated_code, 
                request.source_language
            )
            
            # Create result
            result = TranslationResult(
                translated_code=translated_code,
                source_language=request.source_language,
                translation_success=True,
                translation_time=time.time() - start_time,
                target_language=self.target_language,
                original_size=request.original_size,
                confidence_score=validation_result['confidence_score']
            )
            
            # Add metadata
            result.add_metadata("model_id", self.model_id)
            result.add_metadata("translation_method", "bedrock_ai")
            result.add_metadata("prompt_type", request.source_language)
            result.add_metadata("validation_checks", validation_result['checks'])
            result.add_metadata("quality_metrics", quality_metrics.to_dict() if hasattr(quality_metrics, 'to_dict') else str(quality_metrics))
            result.add_metadata("optimizations_applied", optimizations if 'optimizations' in locals() else [])
            
            # Add any warnings from validation and quality assessment
            for warning in validation_result['warnings']:
                result.add_warning(warning)
            
            for issue in quality_metrics.issues:
                result.add_warning(f"Quality issue: {issue}")
            
            # Update confidence score based on quality metrics
            if hasattr(quality_metrics, 'overall_score'):
                # Combine validation confidence with quality score
                combined_confidence = (validation_result['confidence_score'] + quality_metrics.overall_score) / 2
                result.confidence_score = combined_confidence
            
            logger.info(f"Successfully translated {request.source_language} code using Bedrock")
            return result
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN_CLIENT_ERROR')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            logger.error(f"Bedrock client error: {error_code} - {error_message}")
            
            raise TranslationError(
                f"Bedrock service error: {error_message}",
                error_code=f"BEDROCK_{error_code}",
                original_error=e
            )
            
        except BotoCoreError as e:
            logger.error(f"Boto core error: {str(e)}")
            
            raise TranslationError(
                f"AWS service error: {str(e)}",
                error_code="AWS_SERVICE_ERROR",
                original_error=e
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bedrock response: {str(e)}")
            
            raise TranslationError(
                f"Invalid response format from Bedrock: {str(e)}",
                error_code="INVALID_BEDROCK_RESPONSE",
                original_error=e
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during Bedrock translation: {str(e)}")
            
            raise TranslationError(
                f"Unexpected translation error: {str(e)}",
                error_code="UNEXPECTED_TRANSLATION_ERROR",
                original_error=e
            )
    
    def _validate_translation(self, 
                            source_code: str, 
                            translated_code: str, 
                            source_language: str) -> Dict[str, Any]:
        """
        Validate the quality of the translation.
        
        Args:
            source_code: Original source code
            translated_code: Translated Python code
            source_language: Source programming language
            
        Returns:
            Dict[str, Any]: Validation results with confidence score and warnings
        """
        validation_result = {
            'confidence_score': 0.0,
            'warnings': [],
            'checks': {}
        }
        
        try:
            # Basic validation checks
            checks = {}
            
            # Check 1: Non-empty translation
            if not translated_code or not translated_code.strip():
                validation_result['warnings'].append("Translation resulted in empty code")
                checks['non_empty'] = False
            else:
                checks['non_empty'] = True
            
            # Check 2: Basic Python syntax validation
            try:
                compile(translated_code, '<translated>', 'exec')
                checks['syntax_valid'] = True
            except SyntaxError as e:
                validation_result['warnings'].append(f"Syntax error in translated code: {str(e)}")
                checks['syntax_valid'] = False
            
            # Check 3: Comment preservation
            source_comment_lines = len([line for line in source_code.split('\n') 
                                      if line.strip().startswith(('//','#','/*','*'))])
            translated_comment_lines = len([line for line in translated_code.split('\n') 
                                          if line.strip().startswith('#')])
            
            if source_comment_lines > 0 and translated_comment_lines == 0:
                validation_result['warnings'].append("Comments may not have been preserved")
                checks['comments_preserved'] = False
            else:
                checks['comments_preserved'] = True
            
            # Check 4: Relative size check
            size_ratio = len(translated_code) / max(len(source_code), 1)
            if size_ratio < 0.1:
                validation_result['warnings'].append("Translated code is significantly shorter than original")
                checks['reasonable_size'] = False
            elif size_ratio > 10:
                validation_result['warnings'].append("Translated code is significantly longer than original")
                checks['reasonable_size'] = False
            else:
                checks['reasonable_size'] = True
            
            # Check 5: Python-specific patterns
            has_python_patterns = any(pattern in translated_code for pattern in [
                'def ', 'class ', 'import ', 'from ', 'if __name__'
            ])
            checks['python_patterns'] = has_python_patterns
            
            if not has_python_patterns:
                validation_result['warnings'].append("Translated code lacks typical Python patterns")
            
            # Calculate confidence score
            passed_checks = sum(1 for check in checks.values() if check)
            total_checks = len(checks)
            base_confidence = passed_checks / total_checks if total_checks > 0 else 0
            
            # Adjust confidence based on language complexity
            language_complexity = {
                'javascript': 0.9,
                'typescript': 0.85,
                'java': 0.8,
                'csharp': 0.8,
                'cpp': 0.7,
                'go': 0.85,
                'rust': 0.75
            }
            
            complexity_factor = language_complexity.get(source_language, 0.8)
            validation_result['confidence_score'] = base_confidence * complexity_factor
            validation_result['checks'] = checks
            
        except Exception as e:
            logger.warning(f"Error during translation validation: {str(e)}")
            validation_result['warnings'].append(f"Validation error: {str(e)}")
            validation_result['confidence_score'] = 0.5  # Default moderate confidence
        
        return validation_result
    
    def set_model_parameters(self, 
                           max_tokens: Optional[int] = None,
                           temperature: Optional[float] = None) -> None:
        """
        Update model parameters for translation.
        
        Args:
            max_tokens: Maximum tokens for model response
            temperature: Model temperature (0.0 to 1.0)
        """
        if max_tokens is not None:
            if max_tokens <= 0:
                raise ValueError("max_tokens must be positive")
            self.max_tokens = max_tokens
            logger.debug(f"Updated max_tokens to {max_tokens}")
        
        if temperature is not None:
            if not 0.0 <= temperature <= 1.0:
                raise ValueError("temperature must be between 0.0 and 1.0")
            self.temperature = temperature
            logger.debug(f"Updated temperature to {temperature}")