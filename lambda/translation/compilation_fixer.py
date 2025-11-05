"""
Automatic compilation error fixing system for translated Python code.
"""

import re
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .models import CompilationResult
from .compilation_processor import CompilationProcessor, ErrorDetail, ErrorSeverity
from .bedrock_compiler import BedrockCompiler

logger = logging.getLogger(__name__)


@dataclass
class FixAttempt:
    """Represents a single fix attempt with metadata."""
    attempt_number: int
    original_code: str
    fixed_code: str
    fix_description: str
    errors_targeted: List[str]
    fix_success: bool
    new_errors: List[str]
    fix_time: float


class FixStrategy(Enum):
    """Available fix strategies for different error types."""
    SYNTAX_FIX = "syntax_fix"
    IMPORT_FIX = "import_fix"
    RUNTIME_FIX = "runtime_fix"
    AI_POWERED_FIX = "ai_powered_fix"
    PATTERN_BASED_FIX = "pattern_based_fix"


class CompilationFixer:
    """
    Automatic compilation error fixing system for Python code.
    
    This class analyzes compilation errors and generates targeted fixes
    using pattern matching, rule-based fixes, and AI-powered suggestions.
    """
    
    def __init__(self, bedrock_client, compiler: BedrockCompiler, 
                 max_fix_attempts: int = 3):
        """
        Initialize the compilation fixer.
        
        Args:
            bedrock_client: Bedrock client for AI-powered fixes
            compiler: BedrockCompiler instance for re-compilation
            max_fix_attempts: Maximum number of fix attempts per error
        """
        self.bedrock_client = bedrock_client
        self.compiler = compiler
        self.processor = CompilationProcessor()
        self.max_fix_attempts = max_fix_attempts
        
        # Initialize fix patterns and strategies
        self.fix_patterns = self._initialize_fix_patterns()
        self.import_mappings = self._initialize_import_mappings()
        self.syntax_fixes = self._initialize_syntax_fixes()
        
        # Track fix attempts and success rates
        self.fix_history: List[FixAttempt] = []
        self.fix_success_rate = 0.0
        
        # Infinite loop prevention
        self.code_hash_history: List[str] = []
        self.max_identical_attempts = 2
    
    def _initialize_fix_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize patterns for automatic error fixing.
        
        Returns:
            Dict[str, Dict[str, Any]]: Fix patterns with metadata
        """
        return {
            # Import-related fixes
            "missing_module": {
                "pattern": r"ModuleNotFoundError: No module named '(.+?)'",
                "strategy": FixStrategy.IMPORT_FIX,
                "fix_function": self._fix_missing_module,
                "priority": 1
            },
            "import_error": {
                "pattern": r"ImportError: (.+)",
                "strategy": FixStrategy.IMPORT_FIX,
                "fix_function": self._fix_import_error,
                "priority": 2
            },
            
            # Syntax-related fixes
            "indentation_error": {
                "pattern": r"IndentationError: (.+?) \(line (\d+)\)",
                "strategy": FixStrategy.SYNTAX_FIX,
                "fix_function": self._fix_indentation_error,
                "priority": 1
            },
            "syntax_error": {
                "pattern": r"SyntaxError: (.+?) \(line (\d+)\)",
                "strategy": FixStrategy.SYNTAX_FIX,
                "fix_function": self._fix_syntax_error,
                "priority": 1
            },
            "missing_colon": {
                "pattern": r"SyntaxError: invalid syntax.*?line (\d+)",
                "strategy": FixStrategy.SYNTAX_FIX,
                "fix_function": self._fix_missing_colon,
                "priority": 2
            },
            
            # Runtime-related fixes
            "name_error": {
                "pattern": r"NameError: name '(.+?)' is not defined",
                "strategy": FixStrategy.RUNTIME_FIX,
                "fix_function": self._fix_name_error,
                "priority": 2
            },
            "attribute_error": {
                "pattern": r"AttributeError: '(.+?)' object has no attribute '(.+?)'",
                "strategy": FixStrategy.RUNTIME_FIX,
                "fix_function": self._fix_attribute_error,
                "priority": 3
            },
            "type_error": {
                "pattern": r"TypeError: (.+)",
                "strategy": FixStrategy.RUNTIME_FIX,
                "fix_function": self._fix_type_error,
                "priority": 3
            }
        }
    
    def _initialize_import_mappings(self) -> Dict[str, str]:
        """
        Initialize common import mappings for fixing missing modules.
        
        Returns:
            Dict[str, str]: Module name to import statement mapping
        """
        return {
            # Common JavaScript to Python mappings
            "fs": "import os",
            "path": "import os.path",
            "http": "import urllib.request",
            "https": "import urllib.request",
            "crypto": "import hashlib",
            "util": "import functools",
            
            # Common Java to Python mappings
            "java.util.List": "from typing import List",
            "java.util.Map": "from typing import Dict",
            "java.util.Set": "from typing import Set",
            "java.io.File": "import os",
            "java.lang.String": "# String is built-in in Python",
            
            # Common C# to Python mappings
            "System.Collections.Generic.List": "from typing import List",
            "System.Collections.Generic.Dictionary": "from typing import Dict",
            "System.IO.File": "import os",
            "System.String": "# String is built-in in Python",
            
            # Common missing Python modules
            "requests": "import requests  # pip install requests",
            "numpy": "import numpy as np  # pip install numpy",
            "pandas": "import pandas as pd  # pip install pandas",
            "json": "import json",
            "datetime": "from datetime import datetime",
            "time": "import time",
            "re": "import re",
            "os": "import os",
            "sys": "import sys"
        }
    
    def _initialize_syntax_fixes(self) -> Dict[str, str]:
        """
        Initialize common syntax fix patterns.
        
        Returns:
            Dict[str, str]: Pattern to replacement mapping
        """
        return {
            # Common syntax issues from translation
            r"function\s+(\w+)\s*\(": r"def \1(",  # function to def
            r"var\s+(\w+)\s*=": r"\1 =",  # var declaration
            r"let\s+(\w+)\s*=": r"\1 =",  # let declaration
            r"const\s+(\w+)\s*=": r"\1 =",  # const declaration
            r"console\.log\(": r"print(",  # console.log to print
            r"\.length": r"len()",  # .length to len()
            r"\.push\(": r".append(",  # .push to .append
            r"===": r"==",  # strict equality to equality
            r"!==": r"!=",  # strict inequality to inequality
            r"&&": r" and ",  # logical AND
            r"\|\|": r" or ",  # logical OR
            r"!": r" not ",  # logical NOT
            r"true": r"True",  # boolean true
            r"false": r"False",  # boolean false
            r"null": r"None",  # null to None
            r"undefined": r"None",  # undefined to None
        }
    
    def fix_compilation_errors(self, code: str, compilation_result: CompilationResult) -> Dict[str, Any]:
        """
        Analyze and fix compilation errors in Python code.
        
        Args:
            code: Python source code with errors
            compilation_result: Compilation result containing errors
            
        Returns:
            Dict[str, Any]: Fix results with final code and metadata
        """
        if compilation_result.compilation_success:
            return {
                "success": True,
                "fixed_code": code,
                "fix_attempts": 0,
                "message": "Code compiled successfully, no fixes needed"
            }
        
        logger.info(f"Starting error fixing process for {len(compilation_result.errors)} errors")
        
        # Process compilation result for detailed error analysis
        enhanced_result = self.processor.process_compilation_result(compilation_result, code)
        
        # Get fixable errors and prioritize them
        fixable_errors = self.processor.get_fixable_errors(enhanced_result)
        prioritized_errors = self.processor.prioritize_errors(fixable_errors)
        
        if not prioritized_errors:
            return {
                "success": False,
                "fixed_code": code,
                "fix_attempts": 0,
                "message": "No fixable errors identified",
                "errors": compilation_result.errors
            }
        
        # Attempt iterative fixes
        return self._apply_iterative_fixes(code, prioritized_errors, enhanced_result)
    
    def _apply_iterative_fixes(self, code: str, errors: List[ErrorDetail], 
                             compilation_result: CompilationResult) -> Dict[str, Any]:
        """
        Apply fixes iteratively until code compiles or max attempts reached.
        
        Args:
            code: Source code to fix
            errors: List of prioritized errors to fix
            compilation_result: Original compilation result
            
        Returns:
            Dict[str, Any]: Final fix results
        """
        current_code = code
        total_attempts = 0
        successful_fixes = 0
        fix_attempts = []
        
        # Initialize tracking for infinite loop prevention
        self.code_hash_history.clear()
        previous_error_counts = []
        
        for attempt in range(self.max_fix_attempts):
            if total_attempts >= self.max_fix_attempts:
                logger.warning(f"Reached maximum fix attempts ({self.max_fix_attempts})")
                break
            
            logger.info(f"Fix attempt {attempt + 1}/{self.max_fix_attempts}")
            
            # Check for infinite loops
            if self._detect_infinite_loop(current_code, errors):
                logger.warning("Infinite loop detected in fix attempts, stopping")
                break
            
            # Try to fix the highest priority error
            if not errors:
                logger.info("No more fixable errors found")
                break
            
            current_error = errors[0]
            logger.debug(f"Attempting to fix: {current_error.error_type} - {current_error.message}")
            
            fix_result = self._apply_single_fix(current_code, current_error, attempt + 1)
            
            if fix_result["success"]:
                current_code = fix_result["fixed_code"]
                successful_fixes += 1
                fix_attempts.append(fix_result["fix_attempt"])
                
                # Validate fix success by re-compilation
                validation_result = self._validate_fix_success(current_code, current_error)
                
                if validation_result["compilation_success"]:
                    # Success! Code compiles without errors
                    self._update_fix_statistics(fix_attempts, True)
                    return {
                        "success": True,
                        "fixed_code": current_code,
                        "fix_attempts": total_attempts + 1,
                        "successful_fixes": successful_fixes,
                        "fix_history": fix_attempts,
                        "validation_result": validation_result,
                        "message": f"Successfully fixed all errors in {total_attempts + 1} attempts"
                    }
                else:
                    # Update error list with new errors
                    new_compilation = validation_result["compilation_result"]
                    enhanced_result = self.processor.process_compilation_result(new_compilation, current_code)
                    new_errors = self.processor.prioritize_errors(
                        self.processor.get_fixable_errors(enhanced_result)
                    )
                    
                    # Track error progression to detect if we're making progress
                    current_error_count = len(new_compilation.errors)
                    previous_error_counts.append(current_error_count)
                    
                    # Update fix attempt with new errors found
                    fix_attempts[-1].new_errors = new_compilation.errors
                    
                    # Check if we're making progress
                    if self._is_making_progress(previous_error_counts):
                        errors = new_errors
                        logger.info(f"Progress made: {current_error_count} errors remaining")
                    else:
                        logger.warning("No progress in error reduction, trying different approach")
                        if len(errors) > 1:
                            errors = errors[1:]  # Try next error
                        else:
                            break
            else:
                # Fix failed, try next error or AI-powered fix
                logger.debug(f"Fix failed: {fix_result.get('message', 'Unknown reason')}")
                
                if len(errors) > 1:
                    errors = errors[1:]  # Try next error
                    logger.debug("Trying next error in priority list")
                else:
                    # Try AI-powered fix as last resort
                    logger.info("Attempting AI-powered fix as last resort")
                    ai_fix_result = self._apply_ai_powered_fix(current_code, compilation_result, attempt + 1)
                    if ai_fix_result["success"]:
                        current_code = ai_fix_result["fixed_code"]
                        fix_attempts.append(ai_fix_result["fix_attempt"])
                        successful_fixes += 1
                    break
            
            total_attempts += 1
        
        # Final compilation check and result preparation
        final_compilation = self.compiler.compile_python_code(current_code)
        self._update_fix_statistics(fix_attempts, final_compilation.compilation_success)
        
        return {
            "success": final_compilation.compilation_success,
            "fixed_code": current_code,
            "fix_attempts": total_attempts,
            "successful_fixes": successful_fixes,
            "fix_history": fix_attempts,
            "remaining_errors": final_compilation.errors if not final_compilation.compilation_success else [],
            "final_compilation": final_compilation,
            "progress_tracking": {
                "error_count_progression": previous_error_counts,
                "made_progress": self._is_making_progress(previous_error_counts) if previous_error_counts else False
            },
            "message": f"Applied {successful_fixes} fixes in {total_attempts} attempts. " +
                      ("Code now compiles successfully." if final_compilation.compilation_success 
                       else f"{len(final_compilation.errors)} errors remain.")
        }
    
    def _apply_single_fix(self, code: str, error: ErrorDetail, attempt_number: int) -> Dict[str, Any]:
        """
        Apply a single fix for a specific error.
        
        Args:
            code: Source code to fix
            error: Error detail to fix
            attempt_number: Current attempt number
            
        Returns:
            Dict[str, Any]: Fix result
        """
        start_time = time.time()
        
        # Find matching fix pattern
        fix_pattern = None
        for pattern_name, pattern_info in self.fix_patterns.items():
            if re.search(pattern_info["pattern"], error.message, re.IGNORECASE):
                fix_pattern = pattern_info
                break
        
        if not fix_pattern:
            return {
                "success": False,
                "message": f"No fix pattern found for error: {error.message}"
            }
        
        try:
            # Apply the specific fix function
            fix_function = fix_pattern["fix_function"]
            fixed_code = fix_function(code, error)
            
            if fixed_code == code:
                return {
                    "success": False,
                    "message": f"Fix function did not modify code for error: {error.message}"
                }
            
            fix_time = time.time() - start_time
            
            # Create fix attempt record
            fix_attempt = FixAttempt(
                attempt_number=attempt_number,
                original_code=code,
                fixed_code=fixed_code,
                fix_description=f"Applied {fix_pattern['strategy'].value} for: {error.message}",
                errors_targeted=[error.message],
                fix_success=True,
                new_errors=[],
                fix_time=fix_time
            )
            
            return {
                "success": True,
                "fixed_code": fixed_code,
                "fix_attempt": fix_attempt,
                "message": f"Successfully applied fix for: {error.error_type} error"
            }
            
        except Exception as e:
            logger.error(f"Fix function failed: {str(e)}")
            return {
                "success": False,
                "message": f"Fix function failed: {str(e)}"
            }
    
    def _fix_missing_module(self, code: str, error: ErrorDetail) -> str:
        """
        Fix missing module import errors.
        
        Args:
            code: Source code
            error: Error detail
            
        Returns:
            str: Fixed code
        """
        # Extract module name from error
        match = re.search(r"No module named '(.+?)'", error.message)
        if not match:
            return code
        
        module_name = match.group(1)
        
        # Check if we have a mapping for this module
        if module_name in self.import_mappings:
            import_statement = self.import_mappings[module_name]
            
            # Add import at the top of the file
            lines = code.split('\n')
            
            # Find the right place to insert import (after existing imports)
            insert_index = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')) or line.strip().startswith('#'):
                    insert_index = i + 1
                elif line.strip() and not line.strip().startswith('#'):
                    break
            
            lines.insert(insert_index, import_statement)
            return '\n'.join(lines)
        
        # If no mapping, try to add a generic import
        import_statement = f"import {module_name}"
        lines = code.split('\n')
        lines.insert(0, import_statement)
        return '\n'.join(lines)
    
    def _fix_import_error(self, code: str, error: ErrorDetail) -> str:
        """
        Fix general import errors.
        
        Args:
            code: Source code
            error: Error detail
            
        Returns:
            str: Fixed code
        """
        # Try to identify and fix common import issues
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            if 'import' in line:
                # Fix common import syntax issues
                fixed_line = line
                
                # Fix relative imports that might not work
                if 'from .' in line:
                    fixed_line = line.replace('from .', 'from ')
                
                # Fix wildcard imports
                if 'import *' in line:
                    # Try to be more specific (this is a basic fix)
                    module_name = line.split('from ')[1].split(' import')[0].strip()
                    fixed_line = f"import {module_name}"
                
                if fixed_line != line:
                    lines[i] = fixed_line
                    return '\n'.join(lines)
        
        return code
    
    def _fix_indentation_error(self, code: str, error: ErrorDetail) -> str:
        """
        Fix indentation errors.
        
        Args:
            code: Source code
            error: Error detail
            
        Returns:
            str: Fixed code
        """
        if not error.line_number:
            return code
        
        lines = code.split('\n')
        if error.line_number > len(lines):
            return code
        
        # Fix the specific line's indentation
        line_index = error.line_number - 1
        problem_line = lines[line_index]
        
        # Remove all leading whitespace and re-indent with 4 spaces
        # This is a basic fix - more sophisticated logic could analyze context
        stripped_line = problem_line.lstrip()
        
        if stripped_line:
            # Determine appropriate indentation level based on previous lines
            indent_level = 0
            for i in range(line_index - 1, -1, -1):
                prev_line = lines[i].strip()
                if prev_line.endswith(':'):
                    indent_level = 1
                    break
                elif prev_line and not prev_line.startswith('#'):
                    # Match the indentation of the previous non-empty, non-comment line
                    prev_indent = len(lines[i]) - len(lines[i].lstrip())
                    indent_level = prev_indent // 4
                    break
            
            lines[line_index] = '    ' * indent_level + stripped_line
        
        return '\n'.join(lines)
    
    def _fix_syntax_error(self, code: str, error: ErrorDetail) -> str:
        """
        Fix general syntax errors.
        
        Args:
            code: Source code
            error: Error detail
            
        Returns:
            str: Fixed code
        """
        if not error.line_number:
            return code
        
        lines = code.split('\n')
        if error.line_number > len(lines):
            return code
        
        line_index = error.line_number - 1
        problem_line = lines[line_index]
        
        # Apply common syntax fixes
        fixed_line = problem_line
        
        for pattern, replacement in self.syntax_fixes.items():
            fixed_line = re.sub(pattern, replacement, fixed_line)
        
        # Check for missing colons
        if ('if ' in fixed_line or 'for ' in fixed_line or 'while ' in fixed_line or 
            'def ' in fixed_line or 'class ' in fixed_line) and not fixed_line.rstrip().endswith(':'):
            fixed_line = fixed_line.rstrip() + ':'
        
        lines[line_index] = fixed_line
        return '\n'.join(lines)
    
    def _fix_missing_colon(self, code: str, error: ErrorDetail) -> str:
        """
        Fix missing colon syntax errors.
        
        Args:
            code: Source code
            error: Error detail
            
        Returns:
            str: Fixed code
        """
        if not error.line_number:
            return code
        
        lines = code.split('\n')
        if error.line_number > len(lines):
            return code
        
        line_index = error.line_number - 1
        problem_line = lines[line_index].rstrip()
        
        # Add colon if it's missing from control structures
        if (any(keyword in problem_line for keyword in ['if ', 'for ', 'while ', 'def ', 'class ', 'try', 'except', 'finally', 'with ']) 
            and not problem_line.endswith(':')):
            lines[line_index] = problem_line + ':'
        
        return '\n'.join(lines)
    
    def _fix_name_error(self, code: str, error: ErrorDetail) -> str:
        """
        Fix name errors (undefined variables).
        
        Args:
            code: Source code
            error: Error detail
            
        Returns:
            str: Fixed code
        """
        # Extract variable name from error
        match = re.search(r"name '(.+?)' is not defined", error.message)
        if not match:
            return code
        
        var_name = match.group(1)
        
        # Common variable name fixes
        common_fixes = {
            'true': 'True',
            'false': 'False',
            'null': 'None',
            'undefined': 'None',
            'console': 'print',  # For console.log fixes
        }
        
        if var_name.lower() in common_fixes:
            replacement = common_fixes[var_name.lower()]
            return re.sub(r'\b' + re.escape(var_name) + r'\b', replacement, code)
        
        # If it looks like a constant, define it
        if var_name.isupper():
            lines = code.split('\n')
            lines.insert(0, f"{var_name} = None  # TODO: Define this constant")
            return '\n'.join(lines)
        
        return code
    
    def _fix_attribute_error(self, code: str, error: ErrorDetail) -> str:
        """
        Fix attribute errors.
        
        Args:
            code: Source code
            error: Error detail
            
        Returns:
            str: Fixed code
        """
        # Extract object type and attribute from error
        match = re.search(r"'(.+?)' object has no attribute '(.+?)'", error.message)
        if not match:
            return code
        
        obj_type, attr_name = match.group(1), match.group(2)
        
        # Common attribute fixes
        attribute_fixes = {
            ('str', 'length'): 'len({})',
            ('list', 'length'): 'len({})',
            ('list', 'push'): '{}.append',
            ('str', 'charAt'): '{}[{}]',
            ('str', 'substring'): '{}[{}:{}]',
        }
        
        fix_key = (obj_type, attr_name)
        if fix_key in attribute_fixes:
            # This is a simplified fix - a more complete implementation would
            # need to parse the AST to properly replace method calls
            pattern = r'(\w+)\.' + re.escape(attr_name)
            replacement = attribute_fixes[fix_key]
            if '{}' in replacement:
                replacement = replacement.replace('{}', r'\1')
            return re.sub(pattern, replacement, code)
        
        return code
    
    def _fix_type_error(self, code: str, error: ErrorDetail) -> str:
        """
        Fix type errors.
        
        Args:
            code: Source code
            error: Error detail
            
        Returns:
            str: Fixed code
        """
        # This is a basic implementation - type errors are complex to fix automatically
        # Common type error patterns and fixes could be added here
        
        # Fix string concatenation with non-strings
        if "can't multiply sequence by non-int" in error.message:
            # This suggests string * non-integer, might need str() conversion
            return code  # Would need more sophisticated analysis
        
        if "unsupported operand type" in error.message:
            # Type mismatch in operations, might need type conversion
            return code  # Would need more sophisticated analysis
        
        return code
    
    def _apply_ai_powered_fix(self, code: str, compilation_result: CompilationResult, 
                            attempt_number: int) -> Dict[str, Any]:
        """
        Apply AI-powered fix using Bedrock for complex errors.
        
        Args:
            code: Source code to fix
            compilation_result: Compilation result with errors
            attempt_number: Current attempt number
            
        Returns:
            Dict[str, Any]: AI fix result
        """
        start_time = time.time()
        
        try:
            # Prepare prompt for AI fix
            error_summary = "\n".join(compilation_result.errors[:3])  # Limit to top 3 errors
            
            prompt = f"""
Fix the following Python code compilation errors:

ERRORS:
{error_summary}

CODE:
```python
{code}
```

Please provide only the corrected Python code without explanations. Focus on:
1. Syntax errors (missing colons, indentation)
2. Import errors (missing or incorrect imports)
3. Name errors (undefined variables)
4. Type errors (incorrect operations)

Return only the fixed code:
"""
            
            # Use Bedrock to generate fix
            response = self.bedrock_client.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                body={
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            )
            
            # Parse response
            response_body = response.get('body')
            if response_body:
                # Extract the fixed code from the response
                fixed_code = self._extract_code_from_ai_response(response_body)
                
                if fixed_code and fixed_code != code:
                    fix_time = time.time() - start_time
                    
                    fix_attempt = FixAttempt(
                        attempt_number=attempt_number,
                        original_code=code,
                        fixed_code=fixed_code,
                        fix_description="AI-powered fix using Bedrock",
                        errors_targeted=compilation_result.errors,
                        fix_success=True,
                        new_errors=[],
                        fix_time=fix_time
                    )
                    
                    return {
                        "success": True,
                        "fixed_code": fixed_code,
                        "fix_attempt": fix_attempt,
                        "message": "Applied AI-powered fix"
                    }
            
            return {
                "success": False,
                "message": "AI fix did not produce valid code changes"
            }
            
        except Exception as e:
            logger.error(f"AI-powered fix failed: {str(e)}")
            return {
                "success": False,
                "message": f"AI fix failed: {str(e)}"
            }
    
    def _extract_code_from_ai_response(self, response_body: str) -> Optional[str]:
        """
        Extract Python code from AI response.
        
        Args:
            response_body: Raw response from AI model
            
        Returns:
            Optional[str]: Extracted Python code
        """
        try:
            # Look for code blocks
            code_match = re.search(r'```python\n(.*?)\n```', response_body, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()
            
            # Look for code without explicit markers
            code_match = re.search(r'```\n(.*?)\n```', response_body, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()
            
            # If no code blocks, return the whole response (might be just code)
            if response_body.strip():
                return response_body.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract code from AI response: {str(e)}")
            return None
    
    def get_fix_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about fix attempts and success rates.
        
        Returns:
            Dict[str, Any]: Fix statistics
        """
        if not self.fix_history:
            return {
                "total_attempts": 0,
                "success_rate": 0.0,
                "average_fix_time": 0.0,
                "most_common_errors": []
            }
        
        successful_fixes = [f for f in self.fix_history if f.fix_success]
        total_fix_time = sum(f.fix_time for f in self.fix_history)
        
        # Count error types
        error_counts = {}
        for fix in self.fix_history:
            for error in fix.errors_targeted:
                error_type = self._categorize_error_type(error)
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_attempts": len(self.fix_history),
            "successful_fixes": len(successful_fixes),
            "success_rate": len(successful_fixes) / len(self.fix_history) * 100,
            "average_fix_time": total_fix_time / len(self.fix_history),
            "most_common_errors": sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "fix_strategies_used": list(set(f.fix_description.split()[1] for f in self.fix_history if f.fix_success))
        }
    
    def _categorize_error_type(self, error_message: str) -> str:
        """
        Categorize an error message by type.
        
        Args:
            error_message: Error message to categorize
            
        Returns:
            str: Error category
        """
        error_lower = error_message.lower()
        
        if any(keyword in error_lower for keyword in ['syntax', 'indentation', 'invalid syntax']):
            return "syntax"
        elif any(keyword in error_lower for keyword in ['import', 'module']):
            return "import"
        elif any(keyword in error_lower for keyword in ['name', 'not defined']):
            return "name"
        elif any(keyword in error_lower for keyword in ['type', 'attribute']):
            return "type"
        else:
            return "other"
    
    def _detect_infinite_loop(self, code: str, errors: List[ErrorDetail]) -> bool:
        """
        Detect if we're in an infinite loop of fixes.
        
        Args:
            code: Current code state
            errors: Current error list
            
        Returns:
            bool: True if infinite loop detected
        """
        import hashlib
        
        # Create a hash of the current state (code + error messages)
        state_content = code + "".join(error.message for error in errors)
        state_hash = hashlib.md5(state_content.encode()).hexdigest()
        
        # Check if we've seen this state before
        if state_hash in self.code_hash_history:
            identical_count = self.code_hash_history.count(state_hash)
            if identical_count >= self.max_identical_attempts:
                logger.warning(f"Detected infinite loop: state hash {state_hash[:8]} seen {identical_count} times")
                return True
        
        # Add current state to history
        self.code_hash_history.append(state_hash)
        
        # Keep history manageable
        if len(self.code_hash_history) > 20:
            self.code_hash_history = self.code_hash_history[-20:]
        
        return False
    
    def _validate_fix_success(self, code: str, target_error: ErrorDetail) -> Dict[str, Any]:
        """
        Validate that a fix was successful by re-compiling the code.
        
        Args:
            code: Fixed code to validate
            target_error: The error that was targeted for fixing
            
        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            # Re-compile the code
            compilation_result = self.compiler.compile_python_code(code)
            
            # Check if the specific error was fixed
            target_error_fixed = True
            if compilation_result.errors:
                for error in compilation_result.errors:
                    if target_error.message in error or self._errors_are_similar(target_error.message, error):
                        target_error_fixed = False
                        break
            
            return {
                "compilation_success": compilation_result.compilation_success,
                "target_error_fixed": target_error_fixed,
                "compilation_result": compilation_result,
                "new_error_count": len(compilation_result.errors),
                "validation_time": compilation_result.compilation_time
            }
            
        except Exception as e:
            logger.error(f"Fix validation failed: {str(e)}")
            return {
                "compilation_success": False,
                "target_error_fixed": False,
                "compilation_result": None,
                "error_message": str(e)
            }
    
    def _errors_are_similar(self, error1: str, error2: str) -> bool:
        """
        Check if two error messages are similar (same root cause).
        
        Args:
            error1: First error message
            error2: Second error message
            
        Returns:
            bool: True if errors are similar
        """
        # Extract key parts of error messages for comparison
        def extract_error_key(error_msg: str) -> str:
            # Remove line numbers and specific details
            cleaned = re.sub(r'\(line \d+\)', '', error_msg)
            cleaned = re.sub(r'line \d+', '', cleaned)
            cleaned = re.sub(r"'[^']*'", "'*'", cleaned)  # Replace quoted strings with placeholder
            return cleaned.strip().lower()
        
        key1 = extract_error_key(error1)
        key2 = extract_error_key(error2)
        
        return key1 == key2
    
    def _is_making_progress(self, error_counts: List[int]) -> bool:
        """
        Determine if we're making progress in reducing errors.
        
        Args:
            error_counts: List of error counts from previous attempts
            
        Returns:
            bool: True if progress is being made
        """
        if len(error_counts) < 2:
            return True  # Assume progress on first attempt
        
        # Check if error count is generally decreasing
        recent_counts = error_counts[-3:]  # Look at last 3 attempts
        
        if len(recent_counts) >= 2:
            # Progress if latest count is less than or equal to previous
            latest_progress = recent_counts[-1] <= recent_counts[-2]
            
            # Also check overall trend
            if len(recent_counts) >= 3:
                overall_progress = recent_counts[-1] < recent_counts[0]
                return latest_progress or overall_progress
            
            return latest_progress
        
        return True
    
    def _update_fix_statistics(self, fix_attempts: List[FixAttempt], final_success: bool) -> None:
        """
        Update internal fix statistics based on attempt results.
        
        Args:
            fix_attempts: List of fix attempts made
            final_success: Whether the overall fixing process succeeded
        """
        # Add attempts to history
        self.fix_history.extend(fix_attempts)
        
        # Update success rate
        if self.fix_history:
            successful_attempts = sum(1 for attempt in self.fix_history if attempt.fix_success)
            self.fix_success_rate = (successful_attempts / len(self.fix_history)) * 100
        
        # Log statistics
        logger.info(f"Fix statistics updated: {len(fix_attempts)} new attempts, "
                   f"overall success rate: {self.fix_success_rate:.1f}%")
    
    def reset_fix_history(self) -> None:
        """Reset fix history and statistics."""
        self.fix_history.clear()
        self.code_hash_history.clear()
        self.fix_success_rate = 0.0
        logger.info("Fix history and statistics reset")