"""
Language detection module for identifying programming languages from file extensions and code patterns.
"""

import re
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Detects programming language using file extensions and code patterns.
    Supports JavaScript, Java, C#, C++, Go, Rust, TypeScript, and Python.
    """
    
    def __init__(self):
        # File extension to language mapping
        self.extension_map = {
            # JavaScript/TypeScript
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.mjs': 'javascript',
            '.cjs': 'javascript',
            
            # Java
            '.java': 'java',
            
            # C#
            '.cs': 'csharp',
            
            # C++
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c++': 'cpp',
            '.hpp': 'cpp',
            '.hh': 'cpp',
            '.hxx': 'cpp',
            '.h++': 'cpp',
            '.h': 'cpp',  # Could be C or C++, will use patterns to distinguish
            '.c': 'cpp',  # Treating C as C++ for simplicity
            
            # Go
            '.go': 'go',
            
            # Rust
            '.rs': 'rust',
            
            # Python
            '.py': 'python',
            '.pyw': 'python',
            '.pyi': 'python',
        }
        
        # Code patterns for language identification when extension is ambiguous
        self.language_patterns = {
            'javascript': [
                r'\bfunction\s+\w+\s*\(',
                r'\bconst\s+\w+\s*=',
                r'\blet\s+\w+\s*=',
                r'\bvar\s+\w+\s*=',
                r'require\s*\(',
                r'module\.exports',
                r'console\.log\s*\(',
                r'=>\s*{',
                r'\.then\s*\(',
                r'async\s+function',
            ],
            'typescript': [
                r':\s*\w+\s*=',  # Type annotations
                r'interface\s+\w+',
                r'type\s+\w+\s*=',
                r'export\s+interface',
                r'export\s+type',
                r'import\s+.*\s+from\s+["\']',
                r'<\w+>',  # Generic types
                r'as\s+\w+',  # Type assertions
            ],
            'java': [
                r'\bpublic\s+class\s+\w+',
                r'\bprivate\s+\w+\s+\w+',
                r'\bprotected\s+\w+\s+\w+',
                r'\bpublic\s+static\s+void\s+main',
                r'import\s+java\.',
                r'System\.out\.println',
                r'@Override',
                r'extends\s+\w+',
                r'implements\s+\w+',
            ],
            'csharp': [
                r'\busing\s+System',
                r'\bnamespace\s+\w+',
                r'\bpublic\s+class\s+\w+',
                r'Console\.WriteLine',
                r'\[.*\]',  # Attributes
                r'get\s*;\s*set\s*;',  # Properties
                r'var\s+\w+\s*=',
                r'string\s+\w+',
                r'int\s+\w+',
            ],
            'cpp': [
                r'#include\s*<.*>',
                r'#include\s*".*"',
                r'std::',
                r'cout\s*<<',
                r'cin\s*>>',
                r'using\s+namespace\s+std',
                r'int\s+main\s*\(',
                r'class\s+\w+\s*{',
                r'template\s*<',
                r'nullptr',
            ],
            'go': [
                r'\bpackage\s+\w+',
                r'\bfunc\s+\w+\s*\(',
                r'\bfunc\s+main\s*\(',
                r'import\s*\(',
                r'fmt\.Print',
                r':=',
                r'\bgo\s+\w+\(',
                r'\bchan\s+\w+',
                r'\bdefer\s+',
                r'\brange\s+',
            ],
            'rust': [
                r'\bfn\s+\w+\s*\(',
                r'\bfn\s+main\s*\(',
                r'\blet\s+\w+\s*=',
                r'\blet\s+mut\s+\w+',
                r'println!\s*\(',
                r'use\s+\w+::',
                r'impl\s+\w+',
                r'struct\s+\w+',
                r'enum\s+\w+',
                r'match\s+\w+',
            ],
            'python': [
                r'\bdef\s+\w+\s*\(',
                r'\bclass\s+\w+\s*\(',
                r'\bimport\s+\w+',
                r'\bfrom\s+\w+\s+import',
                r'print\s*\(',
                r'if\s+__name__\s*==\s*["\']__main__["\']',
                r':\s*$',  # Colon at end of line (common in Python)
                r'self\.',
                r'@\w+',  # Decorators
            ],
        }
        
        # Supported languages for translation
        self.supported_languages = {
            'javascript', 'typescript', 'java', 'csharp', 'cpp', 'go', 'rust', 'python'
        }
    
    def detect_language(self, file_path: str, code_content: str) -> str:
        """
        Detects programming language using file extension and code patterns.
        
        Args:
            file_path: Path to the file (used for extension detection)
            code_content: Content of the code file
            
        Returns:
            str: Detected language name or 'unknown' if not detected
        """
        logger.debug(f"Detecting language for file: {file_path}")
        
        # First try extension-based detection
        extension_language = self._detect_by_extension(file_path)
        
        if extension_language and extension_language != 'unknown':
            # For unambiguous extensions, return immediately
            if self._is_unambiguous_extension(file_path):
                logger.info(f"Language detected by extension: {extension_language} for {file_path}")
                return extension_language
            
            # For ambiguous extensions (like .h), use pattern analysis to confirm
            pattern_language = self._detect_by_patterns(code_content)
            
            if pattern_language and pattern_language == extension_language:
                logger.info(f"Language confirmed by patterns: {extension_language} for {file_path}")
                return extension_language
            elif pattern_language and pattern_language in self.supported_languages:
                logger.info(f"Language overridden by patterns: {pattern_language} (was {extension_language}) for {file_path}")
                return pattern_language
            else:
                logger.info(f"Language detected by extension (patterns inconclusive): {extension_language} for {file_path}")
                return extension_language
        
        # If extension detection failed, try pattern-based detection
        pattern_language = self._detect_by_patterns(code_content)
        if pattern_language:
            logger.info(f"Language detected by patterns only: {pattern_language} for {file_path}")
            return pattern_language
        
        logger.warning(f"Could not detect language for file: {file_path}")
        return 'unknown'
    
    def _detect_by_extension(self, file_path: str) -> Optional[str]:
        """
        Detect language based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Optional[str]: Detected language or None if not found
        """
        # Extract extension (handle multiple dots in filename)
        if '.' not in file_path:
            return None
        
        extension = '.' + file_path.split('.')[-1].lower()
        return self.extension_map.get(extension)
    
    def _is_unambiguous_extension(self, file_path: str) -> bool:
        """
        Check if the file extension unambiguously identifies the language.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if extension is unambiguous
        """
        ambiguous_extensions = {'.h', '.c'}  # Could be C or C++
        
        if '.' not in file_path:
            return False
        
        extension = '.' + file_path.split('.')[-1].lower()
        return extension not in ambiguous_extensions
    
    def _detect_by_patterns(self, code_content: str) -> Optional[str]:
        """
        Detect language based on code patterns.
        
        Args:
            code_content: Content of the code file
            
        Returns:
            Optional[str]: Detected language or None if not detected
        """
        if not code_content or not code_content.strip():
            return None
        
        language_scores = {}
        
        # Score each language based on pattern matches
        for language, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, code_content, re.MULTILINE | re.IGNORECASE))
                score += matches
            
            if score > 0:
                language_scores[language] = score
        
        if not language_scores:
            return None
        
        # Return the language with the highest score
        best_language = max(language_scores, key=language_scores.get)
        best_score = language_scores[best_language]
        
        # Require a minimum score to avoid false positives
        min_score = 1
        if best_score >= min_score:
            logger.debug(f"Pattern detection scores: {language_scores}, selected: {best_language}")
            return best_language
        
        return None
    
    def is_supported_language(self, language: str) -> bool:
        """
        Check if the detected language is supported for translation.
        
        Args:
            language: Language name
            
        Returns:
            bool: True if language is supported
        """
        return language in self.supported_languages
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of all supported languages.
        
        Returns:
            List[str]: List of supported language names
        """
        return list(self.supported_languages)
    
    def get_confidence_score(self, file_path: str, code_content: str) -> Tuple[str, float]:
        """
        Get language detection with confidence score.
        
        Args:
            file_path: Path to the file
            code_content: Content of the code file
            
        Returns:
            Tuple[str, float]: (detected_language, confidence_score)
                              confidence_score is between 0.0 and 1.0
        """
        detected_language = self.detect_language(file_path, code_content)
        
        if detected_language == 'unknown':
            return detected_language, 0.0
        
        # Calculate confidence based on detection method
        extension_language = self._detect_by_extension(file_path)
        pattern_language = self._detect_by_patterns(code_content)
        
        if extension_language == detected_language and pattern_language == detected_language:
            # Both methods agree
            confidence = 0.95
        elif extension_language == detected_language and self._is_unambiguous_extension(file_path):
            # Unambiguous extension match
            confidence = 0.90
        elif pattern_language == detected_language:
            # Pattern-based detection only
            confidence = 0.75
        elif extension_language == detected_language:
            # Extension-based detection only
            confidence = 0.80
        else:
            # Fallback
            confidence = 0.60
        
        return detected_language, confidence