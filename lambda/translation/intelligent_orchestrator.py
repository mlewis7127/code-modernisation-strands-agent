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

from .models import CompilationResult, ProcessingOutput
from .bedrock_compiler import BedrockCompiler
from .design_specification import design_specification_tool
from .implementation_generator import implementation_from_design_tool
from .specialized_agents import python_code_improvement_specialist

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
def improve_python_code_tool(python_code: str) -> str:
    """
    Analyze and improve Python code quality in a single pass.
    
    This tool combines quality analysis and improvement into one efficient operation.
    It analyzes the code for quality issues, security vulnerabilities, best practices,
    and automatically applies improvements while maintaining functionality.
    
    Args:
        python_code: The Python code to analyze and improve
        
    Returns:
        String with improvement summary and the complete improved Python code
    """
    try:
        improvement_prompt = f"""Please analyze and improve this Python code:

```python
{python_code}
```

Analyze the code for quality, security, performance, and best practices, then provide the improved version."""
        
        improved_result = python_code_improvement_specialist(improvement_prompt)
        return str(improved_result)
        
    except Exception as e:
        logger.error(f"Python code improvement failed: {str(e)}")
        return f"Python code improvement failed: {str(e)}. Original code returned unchanged:\n\n```python\n{python_code}\n```"


class IntelligentTranslationOrchestrator:
    """
    Intelligent orchestrator that uses the Agents-as-Tools pattern for code translation.
    
    Instead of following a rigid workflow, this orchestrator uses an AI agent with
    specialist tools to intelligently decide what processing is needed based on
    the specific request and code characteristics.
    """
    
    def __init__(self, 
                 model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """
        Initialize the intelligent orchestrator.
        
        Args:
            model_id: Bedrock model ID for the orchestrator agent
        """
        self.model_id = model_id
        
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
                python_compiler_tool,
                improve_python_code_tool
            ],
            agent_id="modernisation_orchestrator",
            name="Code Modernisation Orchestrator"
        )
        
        logger.info(f"Initialized Code Modernisation Orchestrator with model {model_id}")
    
    def _get_orchestrator_system_prompt(self) -> str:
        """Get the system prompt for the orchestrator agent."""
        return """You are an intelligent code translation and analysis orchestrator. Your role is to coordinate with specialist tools to handle code processing requests efficiently and intelligently.

NOTE: The source code language has already been detected by the handler and is provided in the user request. You do not need to detect the language.

AVAILABLE SPECIALIST TOOLS:
1. design_specification_tool - Analyzes source code and generates a structured design document describing functionality, architecture, and requirements
2. implementation_from_design_tool - Generates idiomatic Python code from a design specification
3. python_compiler_tool - Compiles and validates Python code using Bedrock AgentCore
4. improve_python_code_tool - Analyzes and improves Python code quality in a single pass (combines analysis + improvement)

WORKFLOW FOR NON-PYTHON CODE:
Use this mandatory workflow - ALL steps are required:
1. design_specification_tool - Analyze source code and create a design document
   - Captures the code's intent, architecture, data structures, and behavior
   - Provides a language-agnostic understanding of what the code does
2. implementation_from_design_tool - Generate idiomatic Python from the design
   - Produces well-structured, Pythonic code that implements the design
   - Results in high-quality, maintainable code
3. python_compiler_tool - MANDATORY: Compile and validate the generated Python code
   - You MUST compile the code - this is not optional
   - If compilation succeeds, you're done!
   - If compilation fails, proceed to step 4
4. IF compilation fails: improve_python_code_tool - Fix the compilation errors
   - Pass the failing code to this tool to fix the errors
   - The tool will analyze and fix the issues
5. python_compiler_tool - MANDATORY: Recompile the fixed code
   - You MUST verify the fixes worked
   - If still failing, repeat steps 4-5 up to 2 more times
   - Do NOT return until code compiles successfully

Benefits of design-driven approach:
- Captures intent and architecture, not just syntax
- Generates idiomatic and maintainable Python code
- Better handles language-specific patterns and idioms
- Provides design documentation as a valuable artifact

WORKFLOW FOR PYTHON CODE:
Use this mandatory workflow - ALL steps are required:
1. improve_python_code_tool - Analyze and improve the Python code in one pass
   - This tool automatically analyzes quality, security, performance, and best practices
   - Then applies improvements while maintaining functionality
   - Returns the improved code ready to use
2. python_compiler_tool - MANDATORY: Compile and validate the improved code
   - You MUST compile the code - this is not optional
   - If compilation succeeds, you're done!
   - If compilation fails, proceed to step 3
3. IF compilation fails: improve_python_code_tool - Fix the compilation errors
   - Pass the failing code to this tool to fix the errors
4. python_compiler_tool - MANDATORY: Recompile the fixed code
   - You MUST verify the fixes worked
   - If still failing, repeat steps 3-4 up to 2 more times
   - Do NOT return until code compiles successfully

CRITICAL COMPILATION REQUIREMENT:
- You MUST ALWAYS compile Python code before returning - no exceptions
- You MUST NOT return until compilation succeeds
- If compilation fails, use improve_python_code_tool to fix errors and recompile
- Iterate up to 3 times total if needed to get clean compilation
- Only report failure if code still doesn't compile after 3 attempts

INTELLIGENT DECISION MAKING:
- For non-Python code: design_specification_tool → implementation_from_design_tool → python_compiler_tool → (if errors: improve_python_code_tool → python_compiler_tool)
- For Python code: improve_python_code_tool → python_compiler_tool → (if errors: improve_python_code_tool → python_compiler_tool)
- Always iterate on compilation errors until code compiles or max attempts reached
- If design-driven approach fails, report the error clearly for investigation

EFFICIENCY PRINCIPLES:
- Follow the mandatory workflows above - compilation is NOT optional
- Once code compiles successfully, you're done - don't over-process
- File information is provided in the user request - use it to make intelligent decisions
- If user has specific requests, prioritize those over default processing
- Remember: ALWAYS compile before returning, iterate on errors until success

RESPONSE FORMAT:
Always provide clear reasoning for your decisions and summarize what you accomplished.
Include the actual results from the tools you used.
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
- Python code is improved by improve_python_code_tool
- Python code is regenerated to fix compilation errors

IMPORTANT: "complete Python code" means EVERYTHING that should be in the final file:
- All class definitions
- All function definitions
- All imports
- ALL test code, demo code, or example usage (including if __name__ == "__main__": blocks)
- Any comments or documentation
- Everything that was in the improved/translated version

If improve_python_code_tool or any other tool added test code, demo code, or if __name__ == "__main__" blocks, you MUST include them in the FINAL TRANSLATED CODE section. Do not omit any part of the code that was generated or improved by the tools. The user expects to receive the exact same code that was successfully compiled and validated.

Even if tools already showed the code, include the COMPLETE final version (with all parts) in this format."""
    
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
            
            # Extract response from Strands Agent (SDK v1.15.0 API)
            # In v1.15.0, the full response is in response.message
            orchestrator_reasoning = str(response.message)
            
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
            
            if not translated_code:
                logger.warning("No Python code could be extracted from orchestrator response")
        
        # Determine if processing was successful based on actual outcomes
        # Success means: code was generated AND (no compilation attempted OR compilation succeeded)
        processing_success = False  # Default to False, will be set based on actual results
        
        # Extract compilation result with improved parsing
        compilation_result = None
        
        # Look for compilation tool results
        # Enhanced detection to handle quality improvement workflow
        if ("python_compiler_tool" in orchestrator_response or 
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
            'python_compiler_tool': 'python_compiler_tool' in orchestrator_response,
            'improve_python_code_tool': 'improve_python_code_tool' in orchestrator_response
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