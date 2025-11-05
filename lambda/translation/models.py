"""
Data models for translation requests and results.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class TranslationRequest:
    """
    Represents a request to translate source code from one language to another.
    """
    source_code: str
    source_language: str
    file_path: str
    original_size: int
    target_language: str = "python"
    
    # Optional metadata
    file_extension: Optional[str] = None
    encoding: str = "utf-8"
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize computed fields after object creation."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        if self.file_extension is None and '.' in self.file_path:
            self.file_extension = '.' + self.file_path.split('.')[-1].lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'source_code': self.source_code,
            'source_language': self.source_language,
            'file_path': self.file_path,
            'original_size': self.original_size,
            'target_language': self.target_language,
            'file_extension': self.file_extension,
            'encoding': self.encoding,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationRequest':
        """Create instance from dictionary."""
        # Handle timestamp conversion
        timestamp_str = data.get('timestamp')
        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None
        
        return cls(
            source_code=data['source_code'],
            source_language=data['source_language'],
            file_path=data['file_path'],
            original_size=data['original_size'],
            target_language=data.get('target_language', 'python'),
            file_extension=data.get('file_extension'),
            encoding=data.get('encoding', 'utf-8'),
            timestamp=timestamp
        )


@dataclass
class TranslationResult:
    """
    Represents the result of a code translation operation.
    """
    translated_code: str
    source_language: str
    translation_success: bool
    translation_time: float
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Additional result information
    target_language: str = "python"
    original_size: int = 0
    translated_size: int = 0
    confidence_score: float = 0.0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Initialize computed fields after object creation."""
        if self.translated_code:
            self.translated_size = len(self.translated_code.encode('utf-8'))
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the result."""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'translated_code': self.translated_code,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'translation_success': self.translation_success,
            'translation_time': self.translation_time,
            'original_size': self.original_size,
            'translated_size': self.translated_size,
            'confidence_score': self.confidence_score,
            'warnings': self.warnings,
            'metadata': self.metadata,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationResult':
        """Create instance from dictionary."""
        return cls(
            translated_code=data['translated_code'],
            source_language=data['source_language'],
            translation_success=data['translation_success'],
            translation_time=data['translation_time'],
            warnings=data.get('warnings', []),
            metadata=data.get('metadata', {}),
            target_language=data.get('target_language', 'python'),
            original_size=data.get('original_size', 0),
            translated_size=data.get('translated_size', 0),
            confidence_score=data.get('confidence_score', 0.0),
            error_message=data.get('error_message')
        )


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
            'error_message': self.error_message
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
            error_message=data.get('error_message')
        )