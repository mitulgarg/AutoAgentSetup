# mcp_server/tools.py
import os
import re
import inspect # Import inspect here for _get_tool_metadata in this file now
from typing import Callable, Dict, Any # <-- ADD THIS IMPORT

# --- Tool Definitions ---

def external_rest(url: str, auth_token: str = None) -> str:
    """Connect to an external REST API.
    Example: `external_rest("https://api.example.com/data", "your_token")`
    """
    return f"Configured to connect to external REST API at {url}" + (f" with token {auth_token[:5]}..." if auth_token else "")

def document_tool(file_name: str) -> str:
    """
    Configures a document for the agent to use. For demo purposes, asks for a local file path.
    Example: `document_tool("report.pdf")`
    """
    # Simulate saving/processing the file for a demo
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        docs_dir = os.path.join(script_dir, "uploaded_docs")
        os.makedirs(docs_dir, exist_ok=True)
        
        file_path = os.path.join(docs_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('file_content')
        
        return f"Document '{file_name}' configured. Actual file would be processed from {file_path} at runtime."
    
    except Exception as e:
        return f"Error configuring document_tool: {e}"


def calculator_tool() -> str:
    """Perform a basic math calculation.
    Example: `calculator_tool("(100 + 50) / 2")`
    """

    return f"Error configuring calculator: {e}"

def business_object(link_name: str) -> str:
    """Access a business object within the Fusion OpenAPI spec using a given link name.
    Example: `business_object("purchaseOrder")`
    """
    return f"Configured to access Fusion business object: {link_name}"

def deeplink_tool(resource_type: str, resource_id: str) -> str:
    """Create a Fusion deeplink for a specific resource type and ID.
    Example: `deeplink_tool("customer", "CUST001")`
    """
    return f"Configured to create deeplink for {resource_type} with ID {resource_id}"

def email_tool(recipient: str, subject: str = "No Subject", body: str = "No Body") -> str:
    """Send an email to a specified recipient with optional subject and body.
    Example: `email_tool("user@example.com", "Meeting Info", "Hi, the meeting is at 2 PM.")`
    """
    return f"Configured to send email to {recipient} with subject '{subject}'"

def user_context_tool() -> str:
    """Get information about the current user, such as ID, role, and department.
    This tool requires no parameters.
    """
    return "Configured to get user context."

def list_uploaded_documents() -> str:
    """List all documents that have been previously configured/uploaded.
    This tool requires no parameters.
    """
    return "Configured to list uploaded documents."

# A dictionary to easily access tool functions by name
AVAILABLE_TOOLS_MAP = {
    "external_rest": external_rest,
    "document_tool": document_tool,
    "calculator_tool": calculator_tool,
    "email_tool": email_tool,
    "business_object": business_object,
    "deeplink_tool": deeplink_tool,
    "user_context_tool": user_context_tool,
    "list_uploaded_documents": list_uploaded_documents,
}

# Add a description attribute to each tool function based on its docstring
for tool_name, tool_func in AVAILABLE_TOOLS_MAP.items():
    if tool_func.__doc__:
        tool_func.description = tool_func.__doc__.strip().split('\n')[0] # First line of docstring
    else:
        tool_func.description = f"A tool for {tool_name.replace('_', ' ')}."

# Utility function to get metadata for a single tool
def _get_tool_metadata_single(tool_func: Callable) -> Dict[str, Any]:
    """Extracts parameters and their types from a tool function's signature."""
    sig = inspect.signature(tool_func)
    params = []
    for name, param in sig.parameters.items():
        param_type = str(param.annotation) if param.annotation else "Any"
        is_optional = False
        if "typing.Optional" in param_type:
            param_type = param_type.replace("typing.Optional[", "").replace("]", "")
            is_optional = True
        elif param.default is not inspect.Parameter.empty:
            is_optional = True

        params.append({
            "name": name,
            "type": param_type.split('.')[-1], # e.g., 'str' from '<class 'str'>'
            "optional": is_optional
        })
    
    description = getattr(tool_func, 'description', f"A tool for {tool_func.__name__.replace('_', ' ')}.")

    return {
        "tool_name": tool_func.__name__,
        "description": description,
        "parameters": params
    }