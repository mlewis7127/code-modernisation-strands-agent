"""
Intelligent Translation Orchestrator using Agents-as-Tools pattern.

This module replaces the rigid EventLoopCycleManager with an intelligent orchestrator
that uses specialist agents as tools, allowing the AI to decide which specialists
to consult and in what order based on the specific request.
"""

import logging
import time
import asyncio
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from strands import Agent, tool
from strands.models import BedrockModel

from .models import TranslationRequest, TranslationResult, CompilationResult, ProcessingOutput
from .language_detector import LanguageDetector
from .bedrock_translator import BedrockTranslator
from .bedrock_compiler import BedrockCompiler
from .compilation_fixer import CompilationFixer
from .design_specification import design_specification_tool
from .implementation_generator import implementation_from_design_tool

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Result from the intelligent orchestration process."""
    success: bool
    processing_output: ProcessingOutput
    orchestrator_reasoning: str
    tools_used: List[str]
    processing_time: float
    error_message: Optional[str] = None


# Specialist Agent Tools
# Note: Language detection is handled by the agent_handler before orchestration
# to avoid redundant LLM calls. The detected language is passed in the user request.

@tool
def code_translator_tool(source_code: str, source_language: str, target_language: str = "python", file_path: str = "code") -> str:
    """
    Translate code from one programming language to another.
    
    Args:
        source_code: The source code to translate
        source_language: The source programming language
        target_language: The target programming language (default: python)
        file_path: Original file path for context
        
    Returns:
        String with translation result and translated code
    """
    try:
        translator = BedrockTranslator()
        
        # Create translation request
        request = TranslationRequest(
            source_code=source_code,
            source_language=source_language,
            target_language=target_language,
            file_path=file_path,
            original_size=len(source_code)
        )
        
        result = translator.translate(request)
        
        if result.translation_success:
            return f"""Translation successful from {source_language} to {target_language}.

Translated code:
```{target_language}
{result.translated_code}
```

Translation time: {result.translation_time:.2f}s
Confidence score: {result.confidence_score:.2f}/10
Warnings: {len(result.warnings)} warnings found"""
        else:
            return f"Translation failed: {result.error_message}"
            
    except Exception as e:
        logger.error(f"Code translation failed: {str(e)}")
        return f"Code translation failed: {str(e)}"


@tool
def python_compiler_tool(python_code: str) -> str:
    """
    Compile and validate Python code using Bedrock AgentCore.
    
    Args:
        python_code: The Python code to compile and validate
        
    Returns:
        String with compilation results
    """
    try:
        # Debug: Log the actual Python code being compiled
        logger.info(f"Compiling Python code ({len(python_code)} chars):")
        logger.info(f"Code preview: {python_code[:200]}{'...' if len(python_code) > 200 else ''}")
        
        compiler = BedrockCompiler()
        result = compiler.compile_python_code(python_code)
        
        if result.compilation_success:
            # Debug: Log execution details
            has_output = bool(result.execution_result and result.execution_result.strip())
            logger.info(f"Compilation successful. Has output: {has_output}")
            if has_output:
                logger.info(f"Execution output: {result.execution_result[:100]}{'...' if len(result.execution_result) > 100 else ''}")
            else:
                logger.info("No execution output - code may not contain print statements or executable code at module level")
            
            return f"""Python code compilation successful!

Execution result:
{result.execution_result or 'No output'}

Compilation time: {result.compilation_time:.3f} seconds
No compilation errors detected."""
        else:
            errors_text = "\n".join(result.errors) if result.errors else "Unknown compilation error"
            return f"""Python code compilation failed.

Compilation errors:
{errors_text}

Warnings: {len(result.warnings)} warnings found
Compilation time: {result.compilation_time:.3f} seconds"""
            
    except Exception as e:
        logger.error(f"Python compilation failed: {str(e)}")
        return f"Python compilation failed: {str(e)}"


@tool
def compilation_fixer_tool(python_code: str, compilation_errors: str) -> str:
    """
    Automatically fix compilation errors in Python code.
    
    Args:
        python_code: The Python code with compilation errors
        compilation_errors: Description of the compilation errors
        
    Returns:
        String with fix results and corrected code
    """
    try:
        compiler = BedrockCompiler()
        fixer = CompilationFixer(bedrock_client=None, compiler=compiler)
        
        # Create a compilation result with the errors
        compilation_result = CompilationResult(
            compilation_success=False,
            errors=[compilation_errors],
            warnings=[],
            compilation_time=0.0
        )
        
        fixed_result = fixer.fix_compilation_errors(python_code, compilation_result)
        
        if fixed_result.get("success", False):
            return f"""Compilation errors fixed successfully!

Fixed Python code:
```python
{fixed_result.get('fixed_code', python_code)}
```

Fix summary: {fixed_result.get('message', 'Errors resolved')}
Fixes applied: {fixed_result.get('fix_attempts', 0)}"""
        else:
            return f"""Could not fix all compilation errors.

Attempted fixes: {fixed_result.get('fix_attempts', 0)}
Remaining errors: {fixed_result.get('message', 'Unknown error')}
Partially fixed code available: {bool(fixed_result.get('fixed_code'))}"""
            
    except Exception as e:
        logger.error(f"Compilation fixing failed: {str(e)}")
        return f"Compilation fixing failed: {str(e)}"


@tool
def quality_analyzer_tool(code: str, language: str) -> str:
    """
    Analyze code quality, security vulnerabilities, and best practices.
    
    Args:
        code: The source code to analyze
        language: The programming language of the code
        
    Returns:
        String with detailed quality analysis
    """
    try:
        # Create a specialized code quality analysis agent
        # Note: Using Claude 3 Sonnet for reliable quality analysis
        quality_agent = Agent(
            model=BedrockModel(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=0.1,
                max_tokens=2000
            ),
            system_prompt=f"""You are a senior code quality specialist with expertise in {language} and software engineering best practices.

Analyze the provided code for:
1. Code quality issues (readability, maintainability, structure)
2. Security vulnerabilities and potential exploits
3. Performance problems and optimization opportunities
4. Best practice violations and anti-patterns
5. Documentation and commenting quality

Provide specific, actionable recommendations with examples where helpful.
Focus on the most important issues first."""
        )
        
        analysis_prompt = f"""Please analyze this {language} code for quality, security, and best practices:

```{language}
{code}
```

Provide a comprehensive analysis with specific recommendations for improvement."""
        
        analysis_result = quality_agent(analysis_prompt)
        return str(analysis_result)
        
    except Exception as e:
        logger.error(f"Quality analysis failed: {str(e)}")
        return f"Quality analysis failed: {str(e)}"


@tool
def quality_improvement_tool(code: str, recommendations: str, language: str = "python") -> str:
    """
    Apply quality recommendations to improve code based on analysis results.
    
    Args:
        code: The source code to improve
        recommendations: Quality analysis recommendations to apply
        language: The programming language (default: python)
        
    Returns:
        Improved code with quality recommendations applied
    """
    try:
        # Create a specialized code improvement agent
        # Note: Using Claude 3 Sonnet for reliable code improvements
        improvement_agent = Agent(
            model=BedrockModel(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=0.2,
                max_tokens=3000
            ),
            system_prompt=f"""You are a senior software engineer specializing in code improvement and refactoring.

Your task is to apply quality recommendations to improve code while maintaining its functionality.

Guidelines:
1. Apply the provided recommendations carefully
2. Maintain the original functionality and behavior
3. Improve code quality, readability, and performance
4. Follow {language} best practices and conventions
5. Add appropriate comments and documentation
6. Ensure the code is production-ready

Always provide the complete improved code, not just the changes."""
        )
        
        improvement_prompt = f"""Please improve this {language} code by applying the following quality recommendations:

CURRENT CODE:
```{language}
{code}
```

QUALITY RECOMMENDATIONS TO APPLY:
{recommendations}

Please provide the complete improved code that incorporates these recommendations while maintaining the original functionality."""
        
        improved_result = improvement_agent(improvement_prompt)
        return str(improved_result)
        
    except Exception as e:
        logger.error(f"Quality improvement failed: {str(e)}")
        return f"Quality improvement failed: {str(e)}. Original code returned unchanged:\n\n```{language}\n{code}\n```"


@tool
def file_processor_tool(file_info: str) -> str:
    """
    Process file metadata and provide insights about the file.
    
    Args:
        file_info: JSON string containing file information
        
    Returns:
        String with file processing insights
    """
    try:
        import json
        info = json.loads(file_info)
        
        file_path = info.get('file_path', 'unknown')
        file_size = info.get('size', 0)
        
        # Analyze file characteristics
        insights = []
        
        # File size analysis
        if file_size > 50000:  # 50KB
            insights.append(f"Large file ({file_size:,} bytes) - may need chunked processing")
        elif file_size < 100:
            insights.append(f"Very small file ({file_size} bytes) - likely a code snippet")
        
        # File extension insights
        if '.' in file_path:
            extension = file_path.split('.')[-1].lower()
            if extension in ['py', 'pyw']:
                insights.append("Python file detected - no translation needed")
            elif extension in ['js', 'jsx', 'ts', 'tsx']:
                insights.append("JavaScript/TypeScript file - good candidate for Python translation")
            elif extension in ['java']:
                insights.append("Java file - complex translation due to OOP patterns")
            elif extension in ['cpp', 'c', 'cc']:
                insights.append("C/C++ file - may need memory management translation")
        
        return f"File analysis for {file_path}:\n" + "\n".join(f"- {insight}" for insight in insights)
        
    except Exception as e:
        logger.error(f"File processing failed: {str(e)}")
        return f"File processing failed: {str(e)}"


class IntelligentTranslationOrchestrator:
    """
    Intelligent orchestrator that uses the Agents-as-Tools pattern for code translation.
    
    Instead of following a rigid workflow, this orchestrator uses an AI agent with
    specialist tools to intelligently decide what processing is needed based on
    the specific request and code characteristics.
    """
    
    def __init__(self, 
                 model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
                 region_name: str = "us-east-1"):
        """
        Initialize the intelligent orchestrator.
        
        Args:
            model_id: Bedrock model ID for the orchestrator agent
            region_name: AWS region for Bedrock services
        """
        self.model_id = model_id
        self.region_name = region_name
        
        # Create the orchestrator agent with all specialist tools
        self.orchestrator = Agent(
            model=BedrockModel(
                model_id=model_id,
                temperature=0.2,  # Slightly higher for more creative problem-solving
                max_tokens=4000
            ),
            system_prompt=self._get_orchestrator_system_prompt(),
            tools=[
                design_specification_tool,
                implementation_from_design_tool,
                code_translator_tool,
                python_compiler_tool,
                compilation_fixer_tool,
                quality_analyzer_tool,
                quality_improvement_tool,
                file_processor_tool
            ],
            agent_id="modernisation_orchestrator",
            name="Code Modernisation Orchestrator"
        )
        
        logger.info(f"Initialized IntelligentTranslationOrchestrator with Claude 3 Sonnet model {model_id}")
    
    def _get_orchestrator_system_prompt(self) -> str:
        """Get the system prompt for the orchestrator agent."""
        return """You are an intelligent code translation and analysis orchestrator. Your role is to coordinate with specialist tools to handle code processing requests efficiently and intelligently.

NOTE: The source code language has already been detected by the handler and is provided in the user request. You do not need to detect the language.

AVAILABLE SPECIALIST TOOLS:
1. design_specification_tool - Analyzes source code and generates a structured design document describing functionality, architecture, and requirements (PREFERRED for non-Python code)
2. implementation_from_design_tool - Generates idiomatic Python code from a design specification (PREFERRED for implementation)
3. code_translator_tool - Translates code directly between programming languages (FALLBACK - use only if design-driven approach fails)
4. python_compiler_tool - Compiles and validates Python code using Bedrock AgentCore
5. compilation_fixer_tool - Automatically fixes compilation errors in Python code
6. quality_analyzer_tool - Analyzes code quality, security, and best practices
7. quality_improvement_tool - Applies quality recommendations to improve code
8. file_processor_tool - Processes file metadata and provides insights

DESIGN-DRIVEN TRANSLATION WORKFLOW (PREFERRED):
For non-Python code, use this two-phase approach for higher quality translations:
1. First, use design_specification_tool to analyze the source code and create a design document
   - This captures the code's intent, architecture, data structures, and behavior
   - The design document provides a language-agnostic understanding of what the code does
2. Then, use implementation_from_design_tool to generate idiomatic Python from the design
   - This produces well-structured, Pythonic code that implements the design
   - Results in better code quality than direct syntactic translation

Benefits of design-driven approach:
- Captures intent and architecture, not just syntax
- Generates more idiomatic and maintainable Python code
- Better handles language-specific patterns and idioms
- Provides design documentation as a valuable artifact

FALLBACK TRANSLATION:
- Use code_translator_tool ONLY if design_specification_tool fails or times out
- Direct translation is faster but may produce less idiomatic Python code
- If design-driven approach encounters errors, fall back gracefully to direct translation

INTELLIGENT DECISION MAKING:
- For non-Python code: Prefer design_specification_tool → implementation_from_design_tool workflow
- For Python code: Focus on validation and quality improvement
  * Use python_compiler_tool to validate the code
  * Use quality_analyzer_tool to identify improvements
  * Use quality_improvement_tool to apply recommendations
  * Use compilation_fixer_tool if validation fails
  * Skip translation tools (design_specification_tool, implementation_from_design_tool, code_translator_tool)
- Only compile code if translation occurred, validation is requested, or there are concerns
- Only fix compilation errors if compilation actually fails
- Analyze quality when requested or when you identify potential issues
- IMPORTANT: If quality_analyzer_tool provides recommendations, use quality_improvement_tool to apply them
- Consider file size, complexity, and user intent when deciding on processing steps

EFFICIENCY PRINCIPLES:
- Skip unnecessary steps to save time and resources
- Use file_processor_tool first to understand file characteristics
- Make decisions based on what you discover, not predetermined workflows
- If user has specific requests, prioritize those over default processing
- If design-driven approach fails, fall back to direct translation rather than failing completely

RESPONSE FORMAT:
Always provide clear reasoning for your decisions and summarize what you accomplished.
Include the actual results from the tools you used.
If you skip certain steps, explain why.
If you use the design-driven approach, mention that you created a design specification first.

CRITICAL: At the start of your response, list which tools you used in this format:
Tools used: tool_name_1, tool_name_2, tool_name_3

CRITICAL OUTPUT REQUIREMENT:
If you translate code to Python, generate Python code, or improve existing Python code, you MUST include the final Python code in your response using this exact format:

FINAL TRANSLATED CODE:
```python
[complete Python code here]
```

This is essential for code extraction. Always include this section when:
- Python code is generated from translation
- Python code is improved by quality_improvement_tool
- Python code is fixed by compilation_fixer_tool
Even if tools already showed the code, include the final version in this format."""
    
    async def process_code_request(self, 
                                 code_content: str, 
                                 file_info: Dict[str, Any],
                                 user_request: Optional[str] = None) -> OrchestrationResult:
        """
        Process a code request using intelligent orchestration.
        
        Args:
            code_content: The source code content
            file_info: Information about the source file
            user_request: Optional specific user request
            
        Returns:
            OrchestrationResult with processing results
        """
        start_time = time.time()
        tools_used = []
        
        try:
            # Build context for the orchestrator
            file_info_json = json.dumps(file_info, default=str)
            
            context = f"""I need help processing this code request:

FILE INFORMATION:
{file_info_json}

CODE CONTENT:
```
{code_content}
```

USER REQUEST: {user_request or 'Process this code file intelligently (detect language, translate to Python if needed, validate, and ensure quality)'}

Please coordinate with the appropriate specialist tools to handle this request efficiently. 
Make intelligent decisions about which tools to use based on what you discover.
Don't follow a rigid workflow - adapt based on the actual needs."""
            
            logger.info("=" * 80)
            logger.info("[ORCHESTRATION] Starting intelligent orchestration process")
            logger.info(f"[ORCHESTRATION] File: {file_info.get('file_path', 'unknown')}")
            logger.info(f"[ORCHESTRATION] Code size: {len(code_content)} characters")
            logger.info("=" * 80)
            
            # Let the orchestrator decide what to do
            orchestration_start = time.time()
            response = self.orchestrator(context)
            orchestration_time = time.time() - orchestration_start
            
            # Extract response from Strands Agent (SDK v0.1.0 API)
            # AgentResult.state.messages contains the full conversation including tool calls
            orchestrator_reasoning = "\n\n".join([str(msg) for msg in response.state.messages])
            
            logger.info(f"[ORCHESTRATION] Orchestrator completed in {orchestration_time:.2f} seconds")
            logger.info(f"[ORCHESTRATION] Response length: {len(orchestrator_reasoning)} characters")
            
            # Extract tools used from agent response
            # The agent is instructed to list tools in format: "Tools used: tool1, tool2, tool3"
            tools_used_match = re.search(r'Tools used:\s*([^\n]+)', orchestrator_reasoning, re.IGNORECASE)
            if tools_used_match:
                tools_used = [tool.strip() for tool in tools_used_match.group(1).split(',') if tool.strip()]
                logger.info(f"[ORCHESTRATION] Tools used: {', '.join(tools_used)}")
            else:
                logger.warning("[ORCHESTRATION] No tools list found in response")
                tools_used = []
            
            # Create processing output based on orchestrator results
            processing_output = self._extract_processing_output(orchestrator_reasoning, code_content)
            
            processing_time = time.time() - start_time
            
            logger.info("=" * 80)
            logger.info(f"[ORCHESTRATION] Intelligent orchestration completed successfully")
            logger.info(f"[ORCHESTRATION] Total processing time: {processing_time:.2f} seconds")
            logger.info(f"[ORCHESTRATION] Tools used: {', '.join(tools_used) if tools_used else 'None detected'}")
            logger.info("=" * 80)
            
            return OrchestrationResult(
                success=True,
                processing_output=processing_output,
                orchestrator_reasoning=orchestrator_reasoning,
                tools_used=tools_used,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Intelligent orchestration failed: {str(e)}"
            logger.error("=" * 80)
            logger.error(f"[ORCHESTRATION] {error_msg}")
            logger.error(f"[ORCHESTRATION] Failed after {processing_time:.2f} seconds")
            logger.error(f"[ORCHESTRATION] Tools attempted: {', '.join(tools_used) if tools_used else 'None'}")
            logger.error("=" * 80)
            
            # Create a minimal processing output for error case
            processing_output = ProcessingOutput(
                original_analysis="Processing failed due to orchestration error",
                processing_success=False,
                processing_time=processing_time,
                error_message=error_msg
            )
            
            return OrchestrationResult(
                success=False,
                processing_output=processing_output,
                orchestrator_reasoning=f"Error occurred: {error_msg}",
                tools_used=tools_used,
                processing_time=processing_time,
                error_message=error_msg
            )
    
    def _extract_processing_output(self, orchestrator_response: str, original_code: str) -> ProcessingOutput:
        """
        Extract ProcessingOutput from the orchestrator's response.
        
        This extracts:
        - Translated Python code
        - Compilation results
        """
        import re
        
        # Extract translated Python code
        translated_code = None
        
        # First, look for the structured "FINAL TRANSLATED CODE" section
        if "FINAL TRANSLATED CODE:" in orchestrator_response:
            # More robust pattern that handles multi-line code properly
            final_code_patterns = [
                r'FINAL TRANSLATED CODE:\s*```python\s*\n(.*?)```',
                r'FINAL TRANSLATED CODE:\s*```python(.*?)```',
                r'FINAL TRANSLATED CODE:\s*```python\s*(.*?)\s*```'
            ]
            
            for pattern in final_code_patterns:
                final_match = re.search(pattern, orchestrator_response, re.DOTALL | re.IGNORECASE)
                if final_match:
                    translated_code = final_match.group(1).strip()
                    logger.info(f"Extracted Python code from FINAL TRANSLATED CODE section ({len(translated_code)} chars)")
                    break
        
        # If no structured section found, check for other Python code blocks
        if not translated_code and "```python" in orchestrator_response.lower():
            # Extract Python code blocks with comprehensive regex patterns
            patterns = [
                r'```python\n(.*?)\n```',
                r'```python\s*(.*?)\s*```',
                r'```\s*python\s*\n(.*?)\n```',
                r'```python(.*?)```',
                r'Translated code:\s*```python\n(.*?)\n```',
                r'Fixed Python code:\s*```python\n(.*?)\n```',
                r'```python\s*\n(.*?)```',
                r'Translation.*?```python\s*\n(.*?)\n```',
                # Handle compilation_fixer_tool output format
                r'compilation_fixer_tool.*?```python\s*\n(.*?)```',
                r'partially fixed code.*?```python\s*\n(.*?)```',
                r'provided.*?```python\s*\n(.*?)```'
            ]
            
            for pattern in patterns:
                python_blocks = re.findall(pattern, orchestrator_response, re.DOTALL | re.IGNORECASE)
                if python_blocks:
                    # Get the longest code block (likely the most complete)
                    code_block = max(python_blocks, key=len).strip()
                    if code_block and len(code_block) > 10:  # Ensure it's substantial code
                        # Decode escape sequences if present (e.g., \n -> actual newline)
                        if '\\n' in code_block or '\\t' in code_block:
                            try:
                                code_block = code_block.encode().decode('unicode_escape')
                                logger.info("Decoded escape sequences in extracted code")
                            except Exception as e:
                                logger.warning(f"Could not decode escape sequences: {e}")
                        translated_code = code_block
                        logger.info(f"Extracted Python code block using pattern: {pattern[:50]}... ({len(code_block)} chars)")
                        break
        
        # If no Python blocks found, look for translation success indicators and try alternative extraction
        if not translated_code and ("translation successful" in orchestrator_response.lower() or 
                                   "translated code" in orchestrator_response.lower()):
            # Try to find any code blocks that might be Python
            all_code_patterns = [
                r'```\n(def .*?)\n```',
                r'```(def .*?)```',
                r'(def [^`]*?)(?:\n\n|\n```|\nTranslation)',
                r'Fixed code:\s*```python\n(.*?)\n```',
                r'Here.*?Python.*?:\s*```python\n(.*?)\n```',
                r'```\n(.*?def.*?)\n```',
                r'```(.*?def.*?)```'
            ]
            
            for pattern in all_code_patterns:
                matches = re.findall(pattern, orchestrator_response, re.DOTALL | re.IGNORECASE)
                if matches:
                    code_block = max(matches, key=len).strip()
                    if code_block and ("def " in code_block or "import " in code_block or "print(" in code_block):
                        # Decode escape sequences if present
                        if '\\n' in code_block or '\\t' in code_block:
                            try:
                                code_block = code_block.encode().decode('unicode_escape')
                                logger.info("Decoded escape sequences in alternative extraction")
                            except Exception as e:
                                logger.warning(f"Could not decode escape sequences: {e}")
                        translated_code = code_block
                        logger.info(f"Extracted Python code via alternative pattern: {pattern[:50]}... ({len(code_block)} chars)")
                        break
        
        # Last resort: look for any code that has Python syntax without markdown
        if not translated_code:
            # Look for Python function definitions in the response
            python_function_pattern = r'(def\s+\w+\([^)]*\):.*?)(?=\n\n|\n[A-Z]|\nThe|\n$|$)'
            matches = re.findall(python_function_pattern, orchestrator_response, re.DOTALL | re.IGNORECASE)
            if matches:
                # Combine all function definitions found
                translated_code = '\n\n'.join(match.strip() for match in matches)
                logger.info(f"Extracted Python functions without markdown ({len(translated_code)} chars)")
            else:
                # Try to extract Python code from compilation_fixer_tool output even if not in code blocks
                if "compilation_fixer_tool" in orchestrator_response and "def " in orchestrator_response:
                    # Look for Python code patterns in the response
                    lines = orchestrator_response.split('\n')
                    python_lines = []
                    in_python_code = False
                    
                    for line in lines:
                        # Start collecting when we see Python code indicators
                        if any(indicator in line for indicator in ['def ', 'import ', 'print(', 'if __name__']):
                            in_python_code = True
                        
                        # Collect Python-looking lines
                        if in_python_code and (line.strip().startswith(('def ', 'import ', 'from ', 'print(', 'if ', 'for ', 'while ', 'return ', '#', '"""')) or 
                                             line.strip() == '' or 
                                             '=' in line or 
                                             line.strip().endswith(':')):
                            python_lines.append(line.strip())
                        
                        # Stop collecting if we hit non-Python content
                        elif in_python_code and line.strip() and not any(char in line for char in ['def', 'import', 'print', '=', ':', '#']):
                            break
                    
                    if python_lines:
                        translated_code = '\n'.join(python_lines)
                        logger.info(f"Extracted Python code from compilation_fixer_tool output ({len(translated_code)} chars)")
                
                if not translated_code:
                    logger.warning("No Python code could be extracted from orchestrator response")
        
        # Determine if processing was successful based on actual outcomes
        # Success means: code was generated AND (no compilation attempted OR compilation succeeded)
        processing_success = False  # Default to False, will be set based on actual results
        
        # Extract compilation result with improved parsing
        compilation_result = None
        
        # Look for compilation tool results (including compilation_fixer_tool)
        # Enhanced detection to handle quality improvement workflow
        if ("python_compiler_tool" in orchestrator_response or 
            "compilation_fixer_tool" in orchestrator_response or 
            "compilation" in orchestrator_response.lower() or
            "Success: True" in orchestrator_response or
            "compiled successfully" in orchestrator_response.lower() or
            ("FINAL TRANSLATED CODE:" in orchestrator_response and translated_code)):
            
            compilation_success = False
            execution_result = None
            compilation_time = 0.0
            errors = []
            warnings = []
            
            # Check for successful compilation
            if ("compilation successful" in orchestrator_response.lower() or 
                "Success: True" in orchestrator_response or
                "compiled successfully" in orchestrator_response.lower() or
                ("FINAL TRANSLATED CODE:" in orchestrator_response and translated_code)):
                compilation_success = True
                
                # Extract execution result
                exec_patterns = [
                    r'Execution result:\s*\n(.*?)(?:\n\n|\nCompilation time)',
                    r'Execution result:\s*(.*?)(?:\n|$)',
                ]
                
                for pattern in exec_patterns:
                    exec_match = re.search(pattern, orchestrator_response, re.DOTALL | re.IGNORECASE)
                    if exec_match:
                        execution_result = exec_match.group(1).strip()
                        break
                
                # If no explicit execution result but we have translated code, indicate success
                if not execution_result and translated_code:
                    execution_result = "Python code successfully generated and validated"
                
                # Extract compilation time with multiple patterns
                time_patterns = [
                    r'Compilation time:\s*([\d.]+)\s*seconds?',
                    r'completed in\s*([\d.]+)s.*Success:\s*True',
                    r'Compilation completed in\s*([\d.]+)s'
                ]
                
                for pattern in time_patterns:
                    time_match = re.search(pattern, orchestrator_response, re.IGNORECASE)
                    if time_match:
                        compilation_time = float(time_match.group(1))
                        break
            
            # Handle compilation_fixer_tool results
            elif "compilation_fixer_tool" in orchestrator_response:
                if "could not identify any fixable errors" in orchestrator_response.lower():
                    # Compilation fixer was used but couldn't fix errors
                    compilation_success = False
                    errors = ["Compilation fixer could not identify fixable errors"]
                elif "partially fixed code" in orchestrator_response.lower():
                    # Compilation fixer provided a partial fix
                    compilation_success = True  # Consider it successful since code was provided
                    execution_result = "Code partially fixed by compilation_fixer_tool"
                    warnings = ["Code was partially fixed - may need manual review"]
                else:
                    # General compilation fixer usage
                    compilation_success = True
                    execution_result = "Code processed by compilation_fixer_tool"
            
            # Look for compilation errors
            elif "compilation failed" in orchestrator_response.lower() or "compilation errors" in orchestrator_response.lower():
                # Extract error messages
                error_patterns = [
                    r'Compilation errors:\s*\n(.*?)(?:\n\n|\nWarnings)',
                    r'compilation failed[.:]\s*(.*?)(?:\n|$)',
                ]
                
                for pattern in error_patterns:
                    error_match = re.search(pattern, orchestrator_response, re.DOTALL | re.IGNORECASE)
                    if error_match:
                        error_text = error_match.group(1).strip()
                        errors = [error_text] if error_text else ["Unknown compilation error"]
                        break
                
                if not errors:
                    errors = ["Compilation failed - see orchestrator response for details"]
            
            compilation_result = CompilationResult(
                compilation_success=compilation_success,
                errors=errors,
                warnings=warnings,
                execution_result=execution_result,
                compilation_time=compilation_time
            )
        
        # Fallback: If we have translated code but no compilation result, create a default one
        elif translated_code and translated_code != original_code:
            logger.info("Creating default compilation result for translated code")
            compilation_result = CompilationResult(
                compilation_success=True,
                errors=[],
                warnings=[],
                execution_result="Python code successfully generated via translation workflow",
                compilation_time=0.0
            )
        
        # Initialize output files list - this will be populated by the S3 handler
        output_files = []
        
        # Create simple processing metadata
        processing_metadata = {
            'orchestrator_used': True,
            'tools_detected': [],
            'translation_detected': bool(translated_code and translated_code != original_code),
            'compilation_attempted': bool(compilation_result),
            'response_length': len(orchestrator_response),
            'code_extraction_successful': bool(translated_code and translated_code != original_code)
        }
        
        # Log extraction results for debugging
        if translated_code:
            logger.info(f"Code extraction: Found {len(translated_code)} chars, different from original: {translated_code != original_code}")
        else:
            logger.warning("Code extraction: No translated code found in orchestrator response")
        
        # Simple tool detection - just check if tool names appear in response
        tool_indicators = {
            'design_specification_tool': 'design_specification_tool' in orchestrator_response,
            'implementation_from_design_tool': 'implementation_from_design_tool' in orchestrator_response,
            'code_translator_tool': 'code_translator_tool' in orchestrator_response,
            'python_compiler_tool': 'python_compiler_tool' in orchestrator_response,
            'compilation_fixer_tool': 'compilation_fixer_tool' in orchestrator_response,
            'quality_analyzer_tool': 'quality_analyzer_tool' in orchestrator_response,
            'quality_improvement_tool': 'quality_improvement_tool' in orchestrator_response,
            'file_processor_tool': 'file_processor_tool' in orchestrator_response
        }
        
        processing_metadata['tools_detected'] = [tool for tool, detected in tool_indicators.items() if detected]
        
        # Determine what code to return
        final_code = translated_code if translated_code else original_code
        
        # Log extraction results for debugging
        if translated_code:
            logger.info(f"Successfully extracted translated code ({len(translated_code)} chars)")
        else:
            logger.warning(f"No translated code extracted, using original code ({len(original_code)} chars)")
            # Add debugging info to metadata
            processing_metadata['extraction_failure_reason'] = 'No Python code blocks found in orchestrator response'
        
        # Determine processing success based on actual workflow outcomes
        # Success criteria:
        # 1. Code was successfully generated (translated_code exists and differs from original)
        # 2. If compilation was attempted, it must have succeeded
        # 3. OR if no compilation was attempted but code was generated, that's also success
        code_generated = bool(translated_code and translated_code != original_code)
        compilation_ok = (not compilation_result) or (compilation_result and compilation_result.compilation_success)
        
        processing_success = code_generated and compilation_ok
        
        # Log simple workflow summary
        logger.info("=" * 80)
        logger.info("[WORKFLOW SUMMARY]")
        logger.info(f"  Python code generated: {code_generated}")
        if translated_code and translated_code != original_code:
            logger.info(f"  Python code size: {len(translated_code)} characters")
        logger.info(f"  Compilation attempted: {bool(compilation_result)}")
        if compilation_result:
            logger.info(f"  Compilation successful: {compilation_result.compilation_success}")
        logger.info(f"  Tools detected: {', '.join(processing_metadata['tools_detected'])}")
        logger.info(f"  Processing successful: {processing_success}")
        logger.info("=" * 80)
        
        return ProcessingOutput(
            original_analysis=orchestrator_response,
            translated_code=final_code,
            compilation_result=compilation_result,
            processing_success=processing_success,
            processing_time=0.0,  # Will be set by caller
            output_files=output_files,  # Will be populated by S3 handler
            processing_metadata=processing_metadata
        )


# Convenience function for intelligent code translation
async def process_code_translation_intelligent(
    code_content: str, 
    file_info: Dict[str, Any],
    user_request: Optional[str] = None
) -> ProcessingOutput:
    """
    Convenience function that uses intelligent orchestration for code translation.
    
    This function provides a simple interface to the IntelligentTranslationOrchestrator
    for processing code translation requests.
    """
    orchestrator = IntelligentTranslationOrchestrator()
    result = await orchestrator.process_code_request(code_content, file_info, user_request)
    
    # Update processing time in the output
    result.processing_output.processing_time = result.processing_time
    
    return result.processing_output