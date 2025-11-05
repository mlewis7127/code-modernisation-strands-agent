"""
Compilation result processing utilities for enhanced error analysis and extraction.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .models import CompilationResult

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for compilation issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ErrorDetail:
    """Detailed information about a compilation error."""
    message: str
    error_type: str
    severity: ErrorSeverity
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    file_name: Optional[str] = None
    suggestion: Optional[str] = None
    code_context: Optional[str] = None


class CompilationProcessor:
    """
    Advanced compilation result processor for detailed error analysis.
    
    This class provides enhanced parsing and categorization of compilation
    errors, warnings, and success indicators to support automatic fixing.
    """
    
    def __init__(self):
        """Initialize the compilation processor."""
        self.error_patterns = self._initialize_error_patterns()
        self.fix_suggestions = self._initialize_fix_suggestions()
    
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize regex patterns for error detection and categorization.
        
        Returns:
            Dict[str, Dict[str, Any]]: Error patterns with metadata
        """
        return {
            # Syntax Errors
            "syntax_error": {
                "pattern": r"SyntaxError: (.+?) \(line (\d+)\)",
                "type": "syntax",
                "severity": ErrorSeverity.CRITICAL,
                "extract_line": True
            },
            "indentation_error": {
                "pattern": r"IndentationError: (.+?) \(line (\d+)\)",
                "type": "syntax",
                "severity": ErrorSeverity.HIGH,
                "extract_line": True
            },
            "invalid_syntax": {
                "pattern": r"invalid syntax.*?line (\d+)",
                "type": "syntax",
                "severity": ErrorSeverity.CRITICAL,
                "extract_line": True
            },
            
            # Import Errors
            "module_not_found": {
                "pattern": r"ModuleNotFoundError: No module named '(.+?)'",
                "type": "import",
                "severity": ErrorSeverity.HIGH,
                "extract_module": True
            },
            "import_error": {
                "pattern": r"ImportError: (.+)",
                "type": "import",
                "severity": ErrorSeverity.HIGH
            },
            
            # Runtime Errors
            "name_error": {
                "pattern": r"NameError: name '(.+?)' is not defined",
                "type": "runtime",
                "severity": ErrorSeverity.HIGH,
                "extract_variable": True
            },
            "type_error": {
                "pattern": r"TypeError: (.+)",
                "type": "runtime",
                "severity": ErrorSeverity.MEDIUM
            },
            "attribute_error": {
                "pattern": r"AttributeError: '(.+?)' object has no attribute '(.+?)'",
                "type": "runtime",
                "severity": ErrorSeverity.MEDIUM,
                "extract_object_attr": True
            },
            "value_error": {
                "pattern": r"ValueError: (.+)",
                "type": "runtime",
                "severity": ErrorSeverity.MEDIUM
            },
            
            # File and Path Errors
            "file_not_found": {
                "pattern": r"FileNotFoundError: \[Errno 2\] No such file or directory: '(.+?)'",
                "type": "runtime",
                "severity": ErrorSeverity.MEDIUM,
                "extract_file": True
            }
        }
    
    def _initialize_fix_suggestions(self) -> Dict[str, str]:
        """
        Initialize fix suggestions for common error patterns.
        
        Returns:
            Dict[str, str]: Error type to fix suggestion mapping
        """
        return {
            "module_not_found": "Consider installing the missing module or using an alternative import",
            "name_error": "Check if the variable is defined before use or fix the variable name",
            "indentation_error": "Fix indentation to match Python standards (4 spaces per level)",
            "syntax_error": "Review syntax for missing colons, parentheses, or quotes",
            "type_error": "Check data types and ensure compatible operations",
            "attribute_error": "Verify the object has the expected attribute or method",
            "file_not_found": "Check if the file path is correct and the file exists"
        }
    
    def process_compilation_result(self, result: CompilationResult, source_code: str = None) -> CompilationResult:
        """
        Process and enhance a compilation result with detailed error analysis.
        
        Args:
            result: Original compilation result
            source_code: Optional source code for context extraction
            
        Returns:
            CompilationResult: Enhanced compilation result
        """
        if not result.errors:
            return result
        
        # Process each error for detailed analysis
        detailed_errors = []
        
        for error in result.errors:
            error_detail = self._analyze_error(error, source_code)
            detailed_errors.append(error_detail)
        
        # Update result with enhanced error information
        self._update_result_with_details(result, detailed_errors)
        
        return result
    
    def _analyze_error(self, error_message: str, source_code: str = None) -> ErrorDetail:
        """
        Analyze a single error message for detailed information.
        
        Args:
            error_message: Error message to analyze
            source_code: Optional source code for context
            
        Returns:
            ErrorDetail: Detailed error information
        """
        # Try to match against known error patterns
        for pattern_name, pattern_info in self.error_patterns.items():
            match = re.search(pattern_info["pattern"], error_message, re.IGNORECASE)
            
            if match:
                return self._create_error_detail(
                    error_message, pattern_info, match, source_code
                )
        
        # If no pattern matches, create a generic error detail
        return ErrorDetail(
            message=error_message,
            error_type="unknown",
            severity=ErrorSeverity.MEDIUM,
            suggestion="Review the error message for specific guidance"
        )
    
    def _create_error_detail(self, error_message: str, pattern_info: Dict[str, Any], 
                           match: re.Match, source_code: str = None) -> ErrorDetail:
        """
        Create detailed error information from pattern match.
        
        Args:
            error_message: Original error message
            pattern_info: Pattern information
            match: Regex match object
            source_code: Optional source code
            
        Returns:
            ErrorDetail: Detailed error information
        """
        error_detail = ErrorDetail(
            message=error_message,
            error_type=pattern_info["type"],
            severity=pattern_info["severity"]
        )
        
        # Extract line number if available
        if pattern_info.get("extract_line") and len(match.groups()) >= 2:
            try:
                error_detail.line_number = int(match.group(2))
            except (ValueError, IndexError):
                pass
        
        # Extract specific information based on pattern type
        if pattern_info.get("extract_module"):
            error_detail.suggestion = f"Install or import the module: {match.group(1)}"
        elif pattern_info.get("extract_variable"):
            error_detail.suggestion = f"Define the variable '{match.group(1)}' before use"
        elif pattern_info.get("extract_object_attr"):
            obj_type, attr_name = match.group(1), match.group(2)
            error_detail.suggestion = f"Check if '{obj_type}' objects have the '{attr_name}' attribute"
        elif pattern_info.get("extract_file"):
            error_detail.suggestion = f"Ensure the file exists: {match.group(1)}"
        else:
            # Use generic suggestion for the error type
            error_detail.suggestion = self.fix_suggestions.get(
                pattern_info["type"], "Review the error and apply appropriate fixes"
            )
        
        # Extract code context if source code and line number are available
        if source_code and error_detail.line_number:
            error_detail.code_context = self._extract_code_context(
                source_code, error_detail.line_number
            )
        
        return error_detail
    
    def _extract_code_context(self, source_code: str, line_number: int, 
                            context_lines: int = 3) -> str:
        """
        Extract code context around an error line.
        
        Args:
            source_code: Source code
            line_number: Line number with error (1-based)
            context_lines: Number of context lines before and after
            
        Returns:
            str: Code context with line numbers
        """
        lines = source_code.split('\n')
        start_line = max(0, line_number - context_lines - 1)
        end_line = min(len(lines), line_number + context_lines)
        
        context_lines_list = []
        for i in range(start_line, end_line):
            line_num = i + 1
            marker = ">>> " if line_num == line_number else "    "
            context_lines_list.append(f"{marker}{line_num:3d}: {lines[i]}")
        
        return '\n'.join(context_lines_list)
    
    def _update_result_with_details(self, result: CompilationResult, 
                                  detailed_errors: List[ErrorDetail]) -> None:
        """
        Update compilation result with detailed error information.
        
        Args:
            result: Compilation result to update
            detailed_errors: List of detailed error information
        """
        # Clear existing categorized errors and rebuild them
        result.syntax_errors.clear()
        result.runtime_errors.clear()
        result.import_errors.clear()
        
        # Categorize errors based on detailed analysis
        for error_detail in detailed_errors:
            if error_detail.error_type == "syntax":
                result.syntax_errors.append(error_detail.message)
            elif error_detail.error_type == "runtime":
                result.runtime_errors.append(error_detail.message)
            elif error_detail.error_type == "import":
                result.import_errors.append(error_detail.message)
    
    def get_fixable_errors(self, result: CompilationResult) -> List[ErrorDetail]:
        """
        Get a list of errors that are potentially fixable automatically.
        
        Args:
            result: Compilation result to analyze
            
        Returns:
            List[ErrorDetail]: List of fixable errors
        """
        fixable_errors = []
        
        for error in result.errors:
            error_detail = self._analyze_error(error)
            
            # Consider errors fixable based on type and severity
            if (error_detail.error_type in ["syntax", "import", "runtime"] and 
                error_detail.severity in [ErrorSeverity.HIGH, ErrorSeverity.MEDIUM]):
                fixable_errors.append(error_detail)
        
        return fixable_errors
    
    def prioritize_errors(self, errors: List[ErrorDetail]) -> List[ErrorDetail]:
        """
        Prioritize errors for fixing based on severity and type.
        
        Args:
            errors: List of errors to prioritize
            
        Returns:
            List[ErrorDetail]: Prioritized list of errors
        """
        # Define priority order: syntax errors first, then imports, then runtime
        type_priority = {"syntax": 1, "import": 2, "runtime": 3, "unknown": 4}
        severity_priority = {
            ErrorSeverity.CRITICAL: 1,
            ErrorSeverity.HIGH: 2,
            ErrorSeverity.MEDIUM: 3,
            ErrorSeverity.LOW: 4,
            ErrorSeverity.INFO: 5
        }
        
        return sorted(errors, key=lambda e: (
            type_priority.get(e.error_type, 999),
            severity_priority.get(e.severity, 999),
            e.line_number or 999
        ))
    
    def generate_error_summary(self, result: CompilationResult) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of compilation errors.
        
        Args:
            result: Compilation result to summarize
            
        Returns:
            Dict[str, Any]: Error summary with statistics and recommendations
        """
        if not result.errors:
            return {
                "total_errors": 0,
                "error_types": {},
                "severity_distribution": {},
                "recommendations": ["Code compiled successfully"]
            }
        
        # Analyze all errors
        detailed_errors = [self._analyze_error(error) for error in result.errors]
        
        # Count by type
        error_types = {}
        severity_distribution = {}
        
        for error in detailed_errors:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
            severity_name = error.severity.value
            severity_distribution[severity_name] = severity_distribution.get(severity_name, 0) + 1
        
        # Generate recommendations
        recommendations = self._generate_recommendations(detailed_errors)
        
        return {
            "total_errors": len(result.errors),
            "error_types": error_types,
            "severity_distribution": severity_distribution,
            "fixable_errors": len(self.get_fixable_errors(result)),
            "recommendations": recommendations,
            "compilation_time": result.compilation_time,
            "fix_attempts": result.fix_attempts
        }
    
    def _generate_recommendations(self, detailed_errors: List[ErrorDetail]) -> List[str]:
        """
        Generate fix recommendations based on error analysis.
        
        Args:
            detailed_errors: List of detailed error information
            
        Returns:
            List[str]: List of recommendations
        """
        recommendations = []
        
        # Count error types
        syntax_count = sum(1 for e in detailed_errors if e.error_type == "syntax")
        import_count = sum(1 for e in detailed_errors if e.error_type == "import")
        runtime_count = sum(1 for e in detailed_errors if e.error_type == "runtime")
        
        if syntax_count > 0:
            recommendations.append(f"Fix {syntax_count} syntax error(s) first - these prevent code execution")
        
        if import_count > 0:
            recommendations.append(f"Resolve {import_count} import error(s) - check module availability")
        
        if runtime_count > 0:
            recommendations.append(f"Address {runtime_count} runtime error(s) - review variable definitions and types")
        
        # Add specific suggestions for common patterns
        critical_errors = [e for e in detailed_errors if e.severity == ErrorSeverity.CRITICAL]
        if critical_errors:
            recommendations.append("Focus on critical errors first for maximum impact")
        
        if not recommendations:
            recommendations.append("Review error messages for specific guidance")
        
        return recommendations