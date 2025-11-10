"""
Design Specification Tool for generating structured design documents from source code.

This module provides a Strands Agent-based tool that analyzes source code and generates
a comprehensive design specification document describing the code's functionality,
architecture, components, data structures, and behavior.
"""

import logging
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)


@tool
def design_specification_tool(source_code: str, source_language: str, file_path: str) -> str:
    """
    Analyze source code and generate a structured design specification document.
    
    This tool creates a comprehensive design document that describes the code's
    functionality, architecture, and requirements before implementation. This
    design-driven approach produces higher quality translations by ensuring
    the AI understands the code's intent before generating Python.
    
    Args:
        source_code: The complete source code to analyze
        source_language: The detected programming language (e.g., "JavaScript", "Java", "C++")
        file_path: Original file path for context
        
    Returns:
        String containing the design specification in structured markdown format
    """
    import time
    start_time = time.time()
    
    try:
        logger.info(f"[DESIGN-DRIVEN] Starting design specification generation")
        logger.info(f"[DESIGN-DRIVEN] Source language: {source_language}")
        logger.info(f"[DESIGN-DRIVEN] File path: {file_path}")
        logger.info(f"[DESIGN-DRIVEN] Source code size: {len(source_code)} characters")
        
        # Create a specialized design analysis agent
        logger.debug(f"[DESIGN-DRIVEN] Creating design analysis agent with Claude 3 Sonnet")
        design_agent = Agent(
            model=BedrockModel(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=0.1,  # Low temperature for analytical precision
                max_tokens=3000  # Sufficient for detailed design documents
            ),
            system_prompt=_get_design_analysis_system_prompt(source_language)
        )
        
        # Create the analysis prompt
        analysis_prompt = f"""Analyze the following {source_language} code and create a comprehensive design specification:

```{source_language}
{source_code}
```

File path: {file_path}

Please provide a complete design specification following the structure outlined in your instructions."""
        
        logger.debug(f"[DESIGN-DRIVEN] Invoking design analysis agent")
        
        # Generate the design specification
        design_result = design_agent(analysis_prompt)
        design_document = str(design_result)
        
        generation_time = time.time() - start_time
        
        logger.info(f"[DESIGN-DRIVEN] Successfully generated design specification")
        logger.info(f"[DESIGN-DRIVEN] Design document size: {len(design_document)} characters")
        logger.info(f"[DESIGN-DRIVEN] Design generation time: {generation_time:.2f} seconds")
        
        # Log design document structure validation
        has_overview = "## Overview" in design_document or "# Overview" in design_document
        has_functionality = "## Functionality" in design_document
        has_architecture = "## Architecture" in design_document
        has_components = "## Components" in design_document
        
        logger.debug(f"[DESIGN-DRIVEN] Design document structure - Overview: {has_overview}, "
                    f"Functionality: {has_functionality}, Architecture: {has_architecture}, "
                    f"Components: {has_components}")
        
        return design_document
        
    except Exception as e:
        generation_time = time.time() - start_time
        error_msg = f"Design specification generation failed: {str(e)}"
        logger.error(f"[DESIGN-DRIVEN] {error_msg}")
        logger.error(f"[DESIGN-DRIVEN] Failed after {generation_time:.2f} seconds")
        logger.error(f"[DESIGN-DRIVEN] Will fall back to direct translation approach")
        return error_msg


def _get_design_analysis_system_prompt(source_language: str) -> str:
    """
    Get the system prompt for design analysis based on source language.
    
    Args:
        source_language: The programming language being analyzed
        
    Returns:
        System prompt string for the design analysis agent
    """
    return f"""You are a senior software architect and design specialist with deep expertise in {source_language} and software design principles.

Your task is to analyze source code and create a comprehensive design specification document that captures the code's intent, architecture, and requirements. This design will be used to generate a Python implementation, so focus on understanding WHAT the code does and WHY, not just HOW it does it.

DESIGN SPECIFICATION STRUCTURE:

Generate a design document with the following sections:

# Design Specification

## Overview
Provide a high-level description of what the code does, its purpose, and its main responsibilities. Keep this concise but informative (2-4 sentences).

## Functionality
Describe the key features and capabilities in detail. What does this code accomplish? What are its main use cases?

## Architecture
Describe the overall structure and organization. How is the code organized? What are the main architectural patterns used (e.g., MVC, layered, modular)?

## Components
List and describe the major components, classes, modules, or functions. For each component:
- Name and purpose
- Key responsibilities
- Relationships with other components

## Data Structures
Identify and describe the key data types, classes, interfaces, or structures used:
- Data models and their fields
- Important data relationships
- Data validation rules or constraints

## Algorithms and Logic
Describe important algorithms, business logic, or computational approaches:
- Key algorithms and their purpose
- Complex logic flows
- Important calculations or transformations

## Dependencies
List external libraries, APIs, frameworks, or system dependencies:
- External packages/libraries used
- APIs or services called
- System resources accessed (files, network, etc.)

## Input/Output
Describe the expected inputs and outputs:
- Input parameters, formats, or sources
- Output formats or destinations
- Data transformations between input and output

## Error Handling
Describe how errors and edge cases are handled:
- Error handling strategies
- Validation approaches
- Edge cases and boundary conditions

## Special Considerations
Note any language-specific features, performance considerations, or unique aspects:
- {source_language}-specific patterns or idioms
- Performance-critical sections
- Security considerations
- Concurrency or async patterns
- Memory management approaches

ANALYSIS GUIDELINES:

1. Focus on INTENT over IMPLEMENTATION: Understand what the code is trying to achieve, not just how it achieves it
2. Be COMPREHENSIVE: Cover all significant aspects of the code
3. Be SPECIFIC: Include concrete details, not just generic descriptions
4. Be STRUCTURED: Follow the exact section structure provided above
5. Be CLEAR: Write in clear, professional language that a Python developer can understand
6. IDENTIFY PATTERNS: Recognize design patterns, architectural styles, and best practices
7. CONSIDER CONTEXT: Use the file path and code structure to understand the code's role
8. EXTRACT REQUIREMENTS: Identify implicit requirements and constraints from the code

OUTPUT FORMAT:

Provide the complete design specification in markdown format with all sections filled out.
Use clear headings, bullet points, and formatting for readability.
Ensure every section has meaningful content - do not leave sections empty."""
