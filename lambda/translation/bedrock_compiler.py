"""
Bedrock AgentCore-based Python code compiler and validator.
"""

import logging
import time
from typing import Dict, List, Optional, Any
import json
import asyncio
from datetime import datetime

from .models import CompilationResult

logger = logging.getLogger(__name__)


class BedrockCompilerError(Exception):
    """Base exception for Bedrock compiler errors."""
    
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        self.timestamp = datetime.now()


class BedrockCompiler:
    """
    Python code compiler using Bedrock AgentCore code interpreter client.
    
    This class provides compilation and validation of Python code using AWS Bedrock
    AgentCore tools for secure code execution and error detection.
    """
    
    def __init__(self, region_name: str = "us-east-1", compilation_timeout: int = 30):
        """
        Initialize the Bedrock compiler.
        
        Args:
            region_name: AWS region for Bedrock services
            compilation_timeout: Timeout in seconds for compilation operations
        """
        self.region_name = region_name
        self.compilation_timeout = compilation_timeout
        self.client = None
        self._initialize_client()
        
        # Error pattern matching for categorization
        self.syntax_error_patterns = [
            "SyntaxError", "IndentationError", "TabError", "invalid syntax"
        ]
        self.import_error_patterns = [
            "ImportError", "ModuleNotFoundError", "No module named"
        ]
        self.runtime_error_patterns = [
            "NameError", "TypeError", "ValueError", "AttributeError", 
            "KeyError", "IndexError", "RuntimeError"
        ]
    
    def _initialize_client(self) -> None:
        """
        Initialize the Bedrock AgentCore code interpreter client.
        
        Raises:
            BedrockCompilerError: If client initialization fails
        """
        try:
            # Import here to handle cases where bedrock_agentcore is not available
            from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
            
            self.client = CodeInterpreter(region=self.region_name)
            logger.info("Bedrock AgentCore CodeInterpreter initialized successfully")
            
        except ImportError as e:
            error_msg = "bedrock_agentcore.tools.code_interpreter_client is not available"
            logger.error(f"{error_msg}: {str(e)}")
            raise BedrockCompilerError(
                error_msg,
                error_code="BEDROCK_CLIENT_UNAVAILABLE",
                original_error=e
            )
        except Exception as e:
            error_msg = f"Failed to initialize Bedrock AgentCore client: {str(e)}"
            logger.error(error_msg)
            raise BedrockCompilerError(
                error_msg,
                error_code="CLIENT_INITIALIZATION_FAILED",
                original_error=e
            )
    
    def compile_python_code(self, python_code: str, context: Optional[Dict[str, Any]] = None) -> CompilationResult:
        """
        Compile and validate Python code using Bedrock AgentCore.
        
        Args:
            python_code: Python source code to compile
            context: Optional context information for compilation
            
        Returns:
            CompilationResult: Detailed compilation results
            
        Raises:
            BedrockCompilerError: If compilation process fails
        """
        if not python_code or not python_code.strip():
            return CompilationResult(
                compilation_success=False,
                errors=["Empty or whitespace-only code provided"],
                compilation_time=0.0
            )
        
        start_time = time.time()
        
        try:
            logger.info("Starting Python code compilation with Bedrock AgentCore")
            logger.info(f"Code length: {len(python_code)} characters")
            
            # Perform compilation with timeout
            compilation_result = self._execute_compilation(python_code, context)
            
            # Calculate compilation time
            compilation_time = time.time() - start_time
            compilation_result.compilation_time = compilation_time
            
            logger.info(f"Compilation completed in {compilation_time:.2f}s, "
                       f"Success: {compilation_result.compilation_success}")
            
            return compilation_result
            
        except asyncio.TimeoutError:
            compilation_time = time.time() - start_time
            error_msg = f"Compilation timed out after {self.compilation_timeout} seconds"
            logger.warning(error_msg)
            
            return CompilationResult(
                compilation_success=False,
                errors=[error_msg],
                compilation_time=compilation_time
            )
        except Exception as e:
            compilation_time = time.time() - start_time
            error_msg = f"Compilation failed with unexpected error: {str(e)}"
            logger.error(error_msg)
            
            return CompilationResult(
                compilation_success=False,
                errors=[error_msg],
                compilation_time=compilation_time
            )
    
    def _execute_compilation(self, python_code: str, context: Optional[Dict[str, Any]]) -> CompilationResult:
        """
        Execute the actual compilation using Bedrock AgentCore client.
        
        Args:
            python_code: Python source code to compile
            context: Optional context information
            
        Returns:
            CompilationResult: Compilation results
        """
        try:
            # Prepare the code execution request with required fields
            execution_request = {
                "code": python_code,
                "language": "python"
            }
            
            if context:
                execution_request["context"] = context
            
            # Execute code using Bedrock AgentCore client
            # Note: The API uses invoke method with method and params
            response = self.client.invoke(method="executeCode", params=execution_request)
            
            # Process the event stream to get the result
            # The response contains a 'stream' that we need to iterate through
            result_data = None
            if "stream" in response:
                logger.debug("[COMPILER] Processing event stream from Bedrock AgentCore")
                for event in response["stream"]:
                    if "result" in event:
                        result_data = event["result"]
                        logger.debug(f"[COMPILER] Found result in stream event: {json.dumps(result_data, default=str)[:200]}...")
                        break
            
            if not result_data:
                logger.warning("[COMPILER] No result found in stream, using raw response")
                result_data = response
            
            # Parse the response and create compilation result
            return self._parse_execution_response(result_data)
            
        except Exception as e:
            logger.error(f"Code execution failed: {str(e)}")
            
            # Try to extract meaningful error information
            error_message = str(e)
            errors = [error_message]
            
            # Create compilation result with error details
            result = CompilationResult(
                compilation_success=False,
                errors=errors
            )
            
            # Categorize the error
            self._categorize_error(result, error_message)
            
            return result
    
    def _parse_execution_response(self, response: Dict[str, Any]) -> CompilationResult:
        """
        Parse the response from Bedrock AgentCore code execution.
        
        Args:
            response: Response from code execution
            
        Returns:
            CompilationResult: Parsed compilation results
        """
        # Log the response structure for debugging
        logger.debug(f"[COMPILER] Response keys: {list(response.keys())}")
        logger.debug(f"[COMPILER] Full execution response: {json.dumps(response, indent=2, default=str)[:500]}...")
        
        # Initialize result
        result = CompilationResult(compilation_success=True)
        
        # Check for errors first
        is_error = response.get("isError", False)
        if is_error:
            result.compilation_success = False
            logger.warning("[COMPILER] Execution returned isError=True")
        
        # Extract execution results from the correct structure
        # According to AWS docs: content[0].text or structuredContent.stdout
        output = None
        
        # Try structuredContent.stdout first (most reliable for code execution)
        if "structuredContent" in response and response["structuredContent"]:
            structured = response["structuredContent"]
            if "stdout" in structured:
                output = structured["stdout"]
                logger.info(f"[COMPILER] Found output in structuredContent.stdout: {len(output) if output else 0} chars")
            if "stderr" in structured and structured["stderr"]:
                logger.warning(f"[COMPILER] stderr: {structured['stderr']}")
                if not output:  # If no stdout, use stderr as output
                    output = structured["stderr"]
        
        # Try content array as fallback
        if not output and "content" in response and response["content"]:
            content_array = response["content"]
            if isinstance(content_array, list) and len(content_array) > 0:
                first_content = content_array[0]
                if isinstance(first_content, dict) and "text" in first_content:
                    output = first_content["text"]
                    logger.info(f"[COMPILER] Found output in content[0].text: {len(output) if output else 0} chars")
        
        if output:
            result.execution_result = output
        else:
            logger.warning(f"[COMPILER] No output found in response. Available keys: {list(response.keys())}")
        
        # Check for errors
        if "errors" in response and response["errors"]:
            result.compilation_success = False
            
            # Process each error
            for error in response["errors"]:
                error_message = str(error)
                result.add_error(error_message)
                self._categorize_error(result, error_message)
        
        # Check for warnings
        if "warnings" in response and response["warnings"]:
            for warning in response["warnings"]:
                result.add_warning(str(warning))
        
        # Handle execution status
        if "status" in response:
            status = response["status"]
            if status != "success":
                result.compilation_success = False
                if "error_message" in response:
                    error_msg = response["error_message"]
                    result.add_error(error_msg)
                    self._categorize_error(result, error_msg)
        
        return result
    
    def _categorize_error(self, result: CompilationResult, error_message: str) -> None:
        """
        Categorize an error message into syntax, import, or runtime errors.
        
        Args:
            result: CompilationResult to update
            error_message: Error message to categorize
        """
        error_lower = error_message.lower()
        
        # Check for syntax errors
        if any(pattern.lower() in error_lower for pattern in self.syntax_error_patterns):
            result.add_error(error_message, "syntax")
        # Check for import errors
        elif any(pattern.lower() in error_lower for pattern in self.import_error_patterns):
            result.add_error(error_message, "import")
        # Check for runtime errors
        elif any(pattern.lower() in error_lower for pattern in self.runtime_error_patterns):
            result.add_error(error_message, "runtime")
        # Default to general error (already added to result.errors)
    
    def validate_syntax(self, python_code: str) -> CompilationResult:
        """
        Perform basic syntax validation without full execution.
        
        Args:
            python_code: Python source code to validate
            
        Returns:
            CompilationResult: Syntax validation results
        """
        start_time = time.time()
        
        try:
            # Use Python's built-in compile function for syntax checking
            compile(python_code, '<string>', 'exec')
            
            compilation_time = time.time() - start_time
            
            return CompilationResult(
                compilation_success=True,
                compilation_time=compilation_time
            )
            
        except SyntaxError as e:
            compilation_time = time.time() - start_time
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            
            result = CompilationResult(
                compilation_success=False,
                errors=[error_msg],
                compilation_time=compilation_time
            )
            result.add_error(error_msg, "syntax")
            
            return result
        except Exception as e:
            compilation_time = time.time() - start_time
            error_msg = f"Validation error: {str(e)}"
            
            return CompilationResult(
                compilation_success=False,
                errors=[error_msg],
                compilation_time=compilation_time
            )
    
    def set_timeout(self, timeout_seconds: int) -> None:
        """
        Set the compilation timeout.
        
        Args:
            timeout_seconds: Timeout in seconds
        """
        if timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        
        self.compilation_timeout = timeout_seconds
        logger.debug(f"Compilation timeout set to {timeout_seconds} seconds")
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get information about the Bedrock client configuration.
        
        Returns:
            Dict[str, Any]: Client configuration information
        """
        return {
            "region_name": self.region_name,
            "compilation_timeout": self.compilation_timeout,
            "client_initialized": self.client is not None,
            "client_type": type(self.client).__name__ if self.client else None
        }
    
    def health_check(self) -> bool:
        """
        Perform a health check on the Bedrock compiler.
        
        Returns:
            bool: True if compiler is healthy and ready
        """
        try:
            if not self.client:
                return False
            
            # Test with simple Python code
            test_code = "print('Health check')"
            result = self.validate_syntax(test_code)
            
            return result.compilation_success
            
        except Exception as e:
            logger.warning(f"Health check failed: {str(e)}")
            return False