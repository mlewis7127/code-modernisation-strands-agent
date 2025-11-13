"""
Data models for intelligent code translation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class CompilationResult:
    """
    Represents the result of a code compilation operation.
    """
    compilation_success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_result: Optional[str] = None
    compilation_time: float = 0.0
    fix_attempts: int = 0
    
    # Additional compilation information
    syntax_errors: List[str] = field(default_factory=list)
    runtime_errors: List[str] = field(default_factory=list)
    import_errors: List[str] = field(default_factory=list)
    
    def add_error(self, error: str, error_type: str = 'general') -> None:
        """Add an error message with optional categorization."""
        self.errors.append(error)
        
        # Categorize errors for better fix targeting
        if error_type == 'syntax':
            self.syntax_errors.append(error)
        elif error_type == 'runtime':
            self.runtime_errors.append(error)
        elif error_type == 'import':
            self.import_errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if compilation has any errors."""
        return len(self.errors) > 0
    
    def get_error_summary(self) -> str:
        """Get a summary of all errors."""
        if not self.errors:
            return "No errors"
        
        return f"Total errors: {len(self.errors)}, " \
               f"Syntax: {len(self.syntax_errors)}, " \
               f"Runtime: {len(self.runtime_errors)}, " \
               f"Import: {len(self.import_errors)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'compilation_success': self.compilation_success,
            'errors': self.errors,
            'warnings': self.warnings,
            'execution_result': self.execution_result,
            'compilation_time': self.compilation_time,
            'fix_attempts': self.fix_attempts,
            'syntax_errors': self.syntax_errors,
            'runtime_errors': self.runtime_errors,
            'import_errors': self.import_errors
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompilationResult':
        """Create instance from dictionary."""
        return cls(
            compilation_success=data['compilation_success'],
            errors=data.get('errors', []),
            warnings=data.get('warnings', []),
            execution_result=data.get('execution_result'),
            compilation_time=data.get('compilation_time', 0.0),
            fix_attempts=data.get('fix_attempts', 0),
            syntax_errors=data.get('syntax_errors', []),
            runtime_errors=data.get('runtime_errors', []),
            import_errors=data.get('import_errors', [])
        )


@dataclass
class DesignSpecificationResult:
    """
    Result from design specification generation.
    """
    success: bool
    design_document: str
    source_language: str
    analysis_time: float
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'design_document': self.design_document,
            'source_language': self.source_language,
            'analysis_time': self.analysis_time,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DesignSpecificationResult':
        """Create instance from dictionary."""
        return cls(
            success=data['success'],
            design_document=data['design_document'],
            source_language=data['source_language'],
            analysis_time=data['analysis_time'],
            error_message=data.get('error_message')
        )


@dataclass
class ImplementationResult:
    """
    Result from implementation generation.
    """
    success: bool
    python_code: str
    implementation_time: float
    design_document: str
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'python_code': self.python_code,
            'implementation_time': self.implementation_time,
            'design_document': self.design_document,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImplementationResult':
        """Create instance from dictionary."""
        return cls(
            success=data['success'],
            python_code=data['python_code'],
            implementation_time=data['implementation_time'],
            design_document=data['design_document'],
            error_message=data.get('error_message')
        )


@dataclass
class ProcessingOutput:
    """
    Represents the complete output of the translation and compilation process.
    """
    original_analysis: str
    translated_code: Optional[str] = None
    compilation_result: Optional[CompilationResult] = None
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    output_files: List[str] = field(default_factory=list)
    
    # Processing status
    processing_success: bool = True
    processing_time: float = 0.0
    error_message: Optional[str] = None
    
    def add_output_file(self, file_path: str) -> None:
        """Add an output file path to the list."""
        self.output_files.append(file_path)
    
    def add_processing_metadata(self, key: str, value: Any) -> None:
        """Add metadata about the processing."""
        self.processing_metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'original_analysis': self.original_analysis,
            'translated_code': self.translated_code,
            'compilation_result': self.compilation_result.to_dict() if self.compilation_result else None,
            'processing_metadata': self.processing_metadata,
            'output_files': self.output_files,
            'processing_success': self.processing_success,
            'processing_time': self.processing_time,
            'error_message': self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingOutput':
        """Create instance from dictionary."""
        compilation_result_data = data.get('compilation_result')
        compilation_result = CompilationResult.from_dict(compilation_result_data) if compilation_result_data else None
        
        return cls(
            original_analysis=data['original_analysis'],
            translated_code=data.get('translated_code'),
            compilation_result=compilation_result,
            processing_metadata=data.get('processing_metadata', {}),
            output_files=data.get('output_files', []),
            processing_success=data.get('processing_success', True),
            processing_time=data.get('processing_time', 0.0),
            error_message=data.get('error_message'),
        )