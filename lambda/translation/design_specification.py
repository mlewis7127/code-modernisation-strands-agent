"""
Design Specification Tool for generating structured design documents from source code.

This module provides a Strands Agent-based tool that analyzes source code and generates
a comprehensive design specification document describing the code's functionality,
architecture, components, data structures, and behavior.
"""

import logging
from strands import tool
from .specialized_agents import design_analysis_specialist

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
        
        # Create the analysis prompt
        analysis_prompt = f"""Analyze the following {source_language} code and create a comprehensive design specification:

```{source_language}
{source_code}
```

File path: {file_path}
Source language: {source_language}

Please provide a complete design specification following the structure outlined in your instructions."""
        
        logger.debug(f"[DESIGN-DRIVEN] Invoking design analysis specialist agent")
        
        # Generate the design specification using the pre-created specialist agent
        design_result = design_analysis_specialist(analysis_prompt)
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

