"""
Translation quality assurance module for code structure preservation and optimization.
"""

import ast
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Metrics for evaluating translation quality."""
    structure_score: float = 0.0
    functionality_score: float = 0.0
    readability_score: float = 0.0
    overall_score: float = 0.0
    issues: List[str] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.suggestions is None:
            self.suggestions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'structure_score': self.structure_score,
            'functionality_score': self.functionality_score,
            'readability_score': self.readability_score,
            'overall_score': self.overall_score,
            'issues': self.issues,
            'suggestions': self.suggestions
        }


class CodeStructureAnalyzer:
    """
    Analyzes code structure to ensure preservation during translation.
    """
    
    def __init__(self):
        self.function_patterns = {
            'javascript': r'function\s+(\w+)\s*\(',
            'typescript': r'(?:function\s+(\w+)\s*\(|(\w+)\s*:\s*\([^)]*\)\s*=>)',
            'java': r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(',
            'csharp': r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(',
            'cpp': r'(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*{',
            'go': r'func\s+(\w+)\s*\(',
            'rust': r'fn\s+(\w+)\s*\(',
            'python': r'def\s+(\w+)\s*\('
        }
        
        self.class_patterns = {
            'javascript': r'class\s+(\w+)',
            'typescript': r'(?:class|interface)\s+(\w+)',
            'java': r'(?:public|private|protected)?\s*(?:abstract)?\s*class\s+(\w+)',
            'csharp': r'(?:public|private|protected)?\s*(?:abstract)?\s*class\s+(\w+)',
            'cpp': r'class\s+(\w+)',
            'go': r'type\s+(\w+)\s+struct',
            'rust': r'(?:struct|enum)\s+(\w+)',
            'python': r'class\s+(\w+)'
        }
    
    def analyze_structure(self, source_code: str, source_language: str) -> Dict[str, Any]:
        """
        Analyze the structure of source code.
        
        Args:
            source_code: Source code to analyze
            source_language: Programming language of the source code
            
        Returns:
            Dict[str, Any]: Structure analysis results
        """
        analysis = {
            'functions': [],
            'classes': [],
            'imports': [],
            'comments': [],
            'complexity_indicators': {}
        }
        
        try:
            # Extract functions
            if source_language in self.function_patterns:
                pattern = self.function_patterns[source_language]
                functions = re.findall(pattern, source_code, re.MULTILINE)
                analysis['functions'] = [f for f in functions if f]
            
            # Extract classes
            if source_language in self.class_patterns:
                pattern = self.class_patterns[source_language]
                classes = re.findall(pattern, source_code, re.MULTILINE)
                analysis['classes'] = [c for c in classes if c]
            
            # Extract comments
            analysis['comments'] = self._extract_comments(source_code, source_language)
            
            # Extract imports/includes
            analysis['imports'] = self._extract_imports(source_code, source_language)
            
            # Calculate complexity indicators
            analysis['complexity_indicators'] = self._calculate_complexity(source_code)
            
        except Exception as e:
            logger.warning(f"Error analyzing code structure: {str(e)}")
            analysis['error'] = str(e)
        
        return analysis
    
    def compare_structures(self, 
                          source_analysis: Dict[str, Any], 
                          translated_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare structures between source and translated code.
        
        Args:
            source_analysis: Structure analysis of source code
            translated_analysis: Structure analysis of translated code
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        comparison = {
            'function_preservation': 0.0,
            'class_preservation': 0.0,
            'comment_preservation': 0.0,
            'import_mapping': 0.0,
            'overall_preservation': 0.0,
            'issues': [],
            'suggestions': []
        }
        
        try:
            # Compare functions
            source_functions = set(source_analysis.get('functions', []))
            translated_functions = set(translated_analysis.get('functions', []))
            
            if source_functions:
                preserved_functions = len(source_functions.intersection(translated_functions))
                comparison['function_preservation'] = preserved_functions / len(source_functions)
                
                missing_functions = source_functions - translated_functions
                if missing_functions:
                    comparison['issues'].append(f"Missing functions: {', '.join(missing_functions)}")
            else:
                comparison['function_preservation'] = 1.0
            
            # Compare classes
            source_classes = set(source_analysis.get('classes', []))
            translated_classes = set(translated_analysis.get('classes', []))
            
            if source_classes:
                preserved_classes = len(source_classes.intersection(translated_classes))
                comparison['class_preservation'] = preserved_classes / len(source_classes)
                
                missing_classes = source_classes - translated_classes
                if missing_classes:
                    comparison['issues'].append(f"Missing classes: {', '.join(missing_classes)}")
            else:
                comparison['class_preservation'] = 1.0
            
            # Compare comments
            source_comments = len(source_analysis.get('comments', []))
            translated_comments = len(translated_analysis.get('comments', []))
            
            if source_comments > 0:
                comparison['comment_preservation'] = min(translated_comments / source_comments, 1.0)
                if translated_comments < source_comments * 0.5:
                    comparison['issues'].append("Significant loss of comments during translation")
            else:
                comparison['comment_preservation'] = 1.0
            
            # Calculate overall preservation score
            scores = [
                comparison['function_preservation'],
                comparison['class_preservation'],
                comparison['comment_preservation']
            ]
            comparison['overall_preservation'] = sum(scores) / len(scores)
            
        except Exception as e:
            logger.warning(f"Error comparing code structures: {str(e)}")
            comparison['error'] = str(e)
        
        return comparison
    
    def _extract_comments(self, code: str, language: str) -> List[str]:
        """Extract comments from code based on language."""
        comments = []
        
        comment_patterns = {
            'javascript': [r'//.*$', r'/\*.*?\*/'],
            'typescript': [r'//.*$', r'/\*.*?\*/'],
            'java': [r'//.*$', r'/\*.*?\*/', r'/\*\*.*?\*/'],
            'csharp': [r'//.*$', r'/\*.*?\*/', r'///.*$'],
            'cpp': [r'//.*$', r'/\*.*?\*/'],
            'go': [r'//.*$', r'/\*.*?\*/'],
            'rust': [r'//.*$', r'/\*.*?\*/', r'///.*$'],
            'python': [r'#.*$', r'""".*?"""', r"'''.*?'''"]
        }
        
        if language in comment_patterns:
            for pattern in comment_patterns[language]:
                matches = re.findall(pattern, code, re.MULTILINE | re.DOTALL)
                comments.extend(matches)
        
        return [c.strip() for c in comments if c.strip()]
    
    def _extract_imports(self, code: str, language: str) -> List[str]:
        """Extract import/include statements from code."""
        imports = []
        
        import_patterns = {
            'javascript': [r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', r'require\([\'"]([^\'"]+)[\'"]\)'],
            'typescript': [r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]'],
            'java': [r'import\s+([^;]+);'],
            'csharp': [r'using\s+([^;]+);'],
            'cpp': [r'#include\s*[<"]([^>"]+)[>"]'],
            'go': [r'import\s+[\'"]([^\'"]+)[\'"]'],
            'rust': [r'use\s+([^;]+);'],
            'python': [r'import\s+([^\s;]+)', r'from\s+([^\s]+)\s+import']
        }
        
        if language in import_patterns:
            for pattern in import_patterns[language]:
                matches = re.findall(pattern, code, re.MULTILINE)
                imports.extend(matches)
        
        return [i.strip() for i in imports if i.strip()]
    
    def _calculate_complexity(self, code: str) -> Dict[str, int]:
        """Calculate basic complexity indicators."""
        return {
            'lines_of_code': len([line for line in code.split('\n') if line.strip()]),
            'cyclomatic_complexity': code.count('if ') + code.count('for ') + code.count('while ') + code.count('case '),
            'nesting_depth': self._calculate_nesting_depth(code),
            'function_count': len(re.findall(r'(?:def|function|func)\s+\w+', code)),
            'class_count': len(re.findall(r'class\s+\w+', code))
        }
    
    def _calculate_nesting_depth(self, code: str) -> int:
        """Calculate maximum nesting depth in code."""
        max_depth = 0
        current_depth = 0
        
        for char in code:
            if char in '{([':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in '})]':
                current_depth = max(0, current_depth - 1)
        
        return max_depth


class PythonCodeOptimizer:
    """
    Optimizes translated Python code for readability and best practices.
    """
    
    def __init__(self):
        self.optimization_rules = [
            self._optimize_imports,
            self._optimize_formatting,
            self._optimize_naming_conventions,
            self._optimize_docstrings,
            self._optimize_type_hints
        ]
    
    def optimize_code(self, python_code: str) -> Tuple[str, List[str]]:
        """
        Optimize Python code for readability and best practices.
        
        Args:
            python_code: Python code to optimize
            
        Returns:
            Tuple[str, List[str]]: Optimized code and list of optimizations applied
        """
        optimized_code = python_code
        optimizations_applied = []
        
        try:
            # Validate syntax first
            ast.parse(python_code)
            
            # Apply optimization rules
            for rule in self.optimization_rules:
                try:
                    result = rule(optimized_code)
                    if result and len(result) == 2:
                        optimized_code, rule_optimizations = result
                        optimizations_applied.extend(rule_optimizations)
                except Exception as e:
                    logger.warning(f"Optimization rule failed: {str(e)}")
                    continue
            
        except SyntaxError as e:
            logger.warning(f"Cannot optimize code with syntax errors: {str(e)}")
            optimizations_applied.append(f"Skipped optimization due to syntax error: {str(e)}")
        
        return optimized_code, optimizations_applied
    
    def _optimize_imports(self, code: str) -> Tuple[str, List[str]]:
        """Optimize import statements."""
        optimizations = []
        lines = code.split('\n')
        
        # Separate imports from other code
        import_lines = []
        other_lines = []
        in_imports = True
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')) and in_imports:
                import_lines.append(line)
            elif stripped == '' and in_imports:
                import_lines.append(line)
            else:
                if in_imports and stripped:
                    in_imports = False
                other_lines.append(line)
        
        # Sort imports
        if import_lines:
            # Remove empty lines from imports
            import_lines = [line for line in import_lines if line.strip()]
            
            # Sort imports (standard library first, then third-party, then local)
            standard_imports = []
            third_party_imports = []
            local_imports = []
            
            for line in import_lines:
                if any(lib in line for lib in ['os', 'sys', 'json', 'time', 'datetime', 're', 'logging']):
                    standard_imports.append(line)
                elif line.strip().startswith('from .') or line.strip().startswith('import .'):
                    local_imports.append(line)
                else:
                    third_party_imports.append(line)
            
            # Combine sorted imports
            sorted_imports = []
            if standard_imports:
                sorted_imports.extend(sorted(standard_imports))
                sorted_imports.append('')
            if third_party_imports:
                sorted_imports.extend(sorted(third_party_imports))
                sorted_imports.append('')
            if local_imports:
                sorted_imports.extend(sorted(local_imports))
                sorted_imports.append('')
            
            # Remove trailing empty line
            if sorted_imports and sorted_imports[-1] == '':
                sorted_imports.pop()
            
            optimized_code = '\n'.join(sorted_imports + [''] + other_lines)
            optimizations.append("Sorted and organized import statements")
        else:
            optimized_code = code
        
        return optimized_code, optimizations
    
    def _optimize_formatting(self, code: str) -> Tuple[str, List[str]]:
        """Optimize code formatting."""
        optimizations = []
        
        # Remove excessive blank lines
        lines = code.split('\n')
        optimized_lines = []
        blank_count = 0
        
        for line in lines:
            if line.strip() == '':
                blank_count += 1
                if blank_count <= 2:  # Allow maximum 2 consecutive blank lines
                    optimized_lines.append(line)
            else:
                blank_count = 0
                optimized_lines.append(line)
        
        if len(optimized_lines) != len(lines):
            optimizations.append("Removed excessive blank lines")
        
        # Ensure proper spacing around operators
        formatted_code = '\n'.join(optimized_lines)
        
        # Add spaces around operators (basic implementation)
        operator_patterns = [
            (r'(\w)=(\w)', r'\1 = \2'),
            (r'(\w)\+(\w)', r'\1 + \2'),
            (r'(\w)-(\w)', r'\1 - \2'),
            (r'(\w)\*(\w)', r'\1 * \2'),
            (r'(\w)/(\w)', r'\1 / \2'),
        ]
        
        original_formatted = formatted_code
        for pattern, replacement in operator_patterns:
            formatted_code = re.sub(pattern, replacement, formatted_code)
        
        if formatted_code != original_formatted:
            optimizations.append("Added proper spacing around operators")
        
        return formatted_code, optimizations
    
    def _optimize_naming_conventions(self, code: str) -> Tuple[str, List[str]]:
        """Optimize naming conventions for Python."""
        optimizations = []
        
        # Convert camelCase to snake_case for variables and functions
        # This is a basic implementation - a full implementation would need AST parsing
        
        # Find camelCase function definitions
        camel_case_functions = re.findall(r'def\s+([a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*)\s*\(', code)
        
        optimized_code = code
        for func_name in camel_case_functions:
            snake_case_name = self._camel_to_snake(func_name)
            # Replace function definition and calls
            optimized_code = re.sub(
                rf'\b{re.escape(func_name)}\b',
                snake_case_name,
                optimized_code
            )
            optimizations.append(f"Converted function name from {func_name} to {snake_case_name}")
        
        return optimized_code, optimizations
    
    def _optimize_docstrings(self, code: str) -> Tuple[str, List[str]]:
        """Add basic docstrings where missing."""
        optimizations = []
        
        # Find functions without docstrings
        function_pattern = r'(def\s+\w+\s*\([^)]*\)\s*:)\s*\n(\s*)((?!"""|\'\'\'|\s*#)[^\n])'
        
        def add_docstring(match):
            func_def = match.group(1)
            indent = match.group(2)
            next_line = match.group(3)
            
            docstring = f'{func_def}\n{indent}    """\n{indent}    TODO: Add function description.\n{indent}    """\n{indent}{next_line}'
            optimizations.append("Added placeholder docstring")
            return docstring
        
        optimized_code = re.sub(function_pattern, add_docstring, code, flags=re.MULTILINE)
        
        return optimized_code, optimizations
    
    def _optimize_type_hints(self, code: str) -> Tuple[str, List[str]]:
        """Add basic type hints where obvious."""
        optimizations = []
        
        # This is a basic implementation - would need more sophisticated analysis
        # for production use
        
        # Add return type hints for functions that return obvious types
        return_patterns = [
            (r'(def\s+\w+\s*\([^)]*\)\s*:.*?return\s+True|False)', r'\1 -> bool'),
            (r'(def\s+\w+\s*\([^)]*\)\s*:.*?return\s+\d+)', r'\1 -> int'),
            (r'(def\s+\w+\s*\([^)]*\)\s*:.*?return\s+["\'])', r'\1 -> str'),
        ]
        
        optimized_code = code
        for pattern, replacement in return_patterns:
            if re.search(pattern, optimized_code, re.DOTALL):
                # This is a simplified approach - real implementation would be more careful
                pass  # Skip for now to avoid breaking code
        
        return optimized_code, optimizations
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class TranslationQualityAssurance:
    """
    Main quality assurance class for translation validation and optimization.
    """
    
    def __init__(self):
        self.structure_analyzer = CodeStructureAnalyzer()
        self.code_optimizer = PythonCodeOptimizer()
    
    def assess_translation_quality(self, 
                                 source_code: str,
                                 translated_code: str,
                                 source_language: str) -> QualityMetrics:
        """
        Assess the quality of a code translation.
        
        Args:
            source_code: Original source code
            translated_code: Translated Python code
            source_language: Source programming language
            
        Returns:
            QualityMetrics: Quality assessment results
        """
        metrics = QualityMetrics()
        
        try:
            # Analyze structures
            source_analysis = self.structure_analyzer.analyze_structure(source_code, source_language)
            translated_analysis = self.structure_analyzer.analyze_structure(translated_code, 'python')
            
            # Compare structures
            structure_comparison = self.structure_analyzer.compare_structures(
                source_analysis, translated_analysis
            )
            
            metrics.structure_score = structure_comparison['overall_preservation']
            metrics.issues.extend(structure_comparison.get('issues', []))
            
            # Assess functionality preservation (basic checks)
            functionality_score = self._assess_functionality_preservation(
                source_code, translated_code, source_language
            )
            metrics.functionality_score = functionality_score
            
            # Assess readability
            readability_score = self._assess_readability(translated_code)
            metrics.readability_score = readability_score
            
            # Calculate overall score
            metrics.overall_score = (
                metrics.structure_score * 0.4 +
                metrics.functionality_score * 0.4 +
                metrics.readability_score * 0.2
            )
            
            # Generate suggestions
            metrics.suggestions = self._generate_improvement_suggestions(
                metrics, source_analysis, translated_analysis
            )
            
        except Exception as e:
            logger.error(f"Error assessing translation quality: {str(e)}")
            metrics.issues.append(f"Quality assessment error: {str(e)}")
            metrics.overall_score = 0.0
        
        return metrics
    
    def optimize_translated_code(self, python_code: str) -> Tuple[str, List[str]]:
        """
        Optimize translated Python code for readability and best practices.
        
        Args:
            python_code: Python code to optimize
            
        Returns:
            Tuple[str, List[str]]: Optimized code and list of optimizations applied
        """
        return self.code_optimizer.optimize_code(python_code)
    
    def _assess_functionality_preservation(self, 
                                         source_code: str,
                                         translated_code: str,
                                         source_language: str) -> float:
        """Assess how well functionality is preserved."""
        score = 0.0
        
        try:
            # Check if translated code is syntactically valid
            ast.parse(translated_code)
            score += 0.3
            
            # Check for presence of main logic patterns
            if 'def ' in translated_code or 'class ' in translated_code:
                score += 0.2
            
            # Check for proper error handling
            if 'try:' in translated_code or 'except' in translated_code:
                score += 0.1
            
            # Check for imports (suggests proper dependency handling)
            if 'import ' in translated_code:
                score += 0.1
            
            # Check relative complexity preservation
            source_complexity = len(source_code.split('\n'))
            translated_complexity = len(translated_code.split('\n'))
            
            if source_complexity > 0:
                complexity_ratio = translated_complexity / source_complexity
                if 0.5 <= complexity_ratio <= 2.0:  # Reasonable size ratio
                    score += 0.3
                else:
                    score += 0.1
            
        except SyntaxError:
            # Syntax errors significantly impact functionality
            score = max(0.0, score - 0.5)
        except Exception as e:
            logger.warning(f"Error assessing functionality: {str(e)}")
            score = 0.5  # Default moderate score
        
        return min(1.0, score)
    
    def _assess_readability(self, python_code: str) -> float:
        """Assess code readability."""
        score = 0.0
        
        try:
            lines = python_code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            if not non_empty_lines:
                return 0.0
            
            # Check for proper indentation
            indented_lines = [line for line in non_empty_lines if line.startswith('    ')]
            if indented_lines:
                score += 0.2
            
            # Check for comments/docstrings
            comment_lines = [line for line in lines if line.strip().startswith('#') or '"""' in line]
            if comment_lines:
                comment_ratio = len(comment_lines) / len(non_empty_lines)
                score += min(0.3, comment_ratio * 2)  # Up to 0.3 for good commenting
            
            # Check for reasonable line length
            long_lines = [line for line in lines if len(line) > 100]
            if len(long_lines) / max(len(non_empty_lines), 1) < 0.1:  # Less than 10% long lines
                score += 0.2
            
            # Check for proper naming (snake_case functions)
            snake_case_functions = re.findall(r'def\s+([a-z_][a-z0-9_]*)\s*\(', python_code)
            camel_case_functions = re.findall(r'def\s+([a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*)\s*\(', python_code)
            
            total_functions = len(snake_case_functions) + len(camel_case_functions)
            if total_functions > 0:
                naming_score = len(snake_case_functions) / total_functions
                score += naming_score * 0.3
            else:
                score += 0.1  # No functions to evaluate
            
        except Exception as e:
            logger.warning(f"Error assessing readability: {str(e)}")
            score = 0.5  # Default moderate score
        
        return min(1.0, score)
    
    def _generate_improvement_suggestions(self, 
                                        metrics: QualityMetrics,
                                        source_analysis: Dict[str, Any],
                                        translated_analysis: Dict[str, Any]) -> List[str]:
        """Generate suggestions for improving translation quality."""
        suggestions = []
        
        # Structure-based suggestions
        if metrics.structure_score < 0.8:
            suggestions.append("Consider reviewing function and class name preservation")
            
            source_functions = len(source_analysis.get('functions', []))
            translated_functions = len(translated_analysis.get('functions', []))
            
            if source_functions > translated_functions:
                suggestions.append("Some functions may be missing in the translation")
        
        # Functionality-based suggestions
        if metrics.functionality_score < 0.7:
            suggestions.append("Review the translated code for syntax errors and logical consistency")
            suggestions.append("Ensure all imports and dependencies are properly handled")
        
        # Readability-based suggestions
        if metrics.readability_score < 0.6:
            suggestions.append("Improve code formatting and add comments/docstrings")
            suggestions.append("Consider using Python naming conventions (snake_case)")
            suggestions.append("Break down long lines for better readability")
        
        # Overall suggestions
        if metrics.overall_score < 0.5:
            suggestions.append("Consider manual review and refinement of the translation")
        
        return suggestions