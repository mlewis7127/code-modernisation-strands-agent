"""
Documentation: Intelligent Translation Orchestrator Code Examples

This file contains code examples and patterns used in the intelligent orchestrator.
It is for documentation purposes only and is not imported by the application.
"""

# Example 1: Simple Tool Pattern
# Tools are functions decorated with @tool that the orchestrator can call

@tool
def python_compiler_tool(python_code: str) -> str:
    """
    Compile Python code using Bedrock AgentCore.
    
    This is a simple tool that wraps a service call.
    """
    compiler = BedrockCompiler()
    result = compiler.compile_python_code(python_code)
    return str(result)


# Example 2: Agents-as-Tools Pattern (Recommended Approach)
# Specialized agents are defined in a separate module and imported
# This is more efficient as agents are created once, not on every tool call

# In specialized_agents.py:
quality_analysis_specialist = Agent(
    model=BedrockModel(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        temperature=0.1,
        max_tokens=2000
    ),
    system_prompt="You are a senior code quality specialist...",
    agent_id="quality_analysis_specialist",
    name="Code Quality Analysis Specialist"
)

# In intelligent_orchestrator.py:
from .specialized_agents import quality_analysis_specialist

@tool
def quality_analyzer_tool(code: str, language: str) -> str:
    """
    Analyze code quality using a pre-created specialist agent.
    
    This demonstrates the recommended Agents-as-Tools pattern where
    specialized agents are defined once and reused across tool calls.
    """
    analysis_prompt = f"Analyze this {language} code: {code}"
    
    # Reuse the pre-created specialist agent
    result = quality_analysis_specialist(analysis_prompt)
    return str(result)


# Example 3: Building Context for the Orchestrator
# This shows how to format the context string that gets passed to the orchestrator

def example_process_code_request(code_content, file_info, user_request):
    """
    Example of how to build and send a request to the orchestrator.
    
    The context string should be clean without extra indentation.
    """
    file_info_json = json.dumps(file_info, default=str)
    
    # Build context with proper formatting (no extra indentation)
    context = f"""I need help processing this code request:

FILE INFORMATION:
{file_info_json}

CODE CONTENT:
```
{code_content}
```

USER REQUEST: {user_request or (
    'Process this code file intelligently '
    '(detect language, translate to Python if needed, validate, and ensure quality)'
)}

Please coordinate with the appropriate specialist tools to handle this request efficiently. 
Make intelligent decisions about which tools to use based on what you discover.
Don't follow a rigid workflow - adapt based on the actual needs."""
    
    # Call the orchestrator (this invokes the AI agent)
    response = self.orchestrator(context)
    
    return response


# Example 4: Creating the Orchestrator Agent
# This shows how the orchestrator agent is initialized with tools

def example_init_orchestrator(model_id):
    """
    Example of how the orchestrator agent is created.
    
    The agent is configured with:
    - A language model (Claude 3 Sonnet via Bedrock)
    - A system prompt defining its role and behavior
    - A list of tools it can use
    - Identity information (agent_id and name)
    """
    orchestrator = Agent(
        model=BedrockModel(
            model_id=model_id,
            temperature=0.2,  # Slightly higher for more creative problem-solving
            max_tokens=4000
        ),
        system_prompt=get_orchestrator_system_prompt(),
        tools=[
            design_specification_tool,
            implementation_from_design_tool,
            code_translator_tool,
            python_compiler_tool,
            quality_analyzer_tool,
            quality_improvement_tool
        ],
        agent_id="modernisation_orchestrator",
        name="Code Modernisation Orchestrator"
    )
    
    return orchestrator

