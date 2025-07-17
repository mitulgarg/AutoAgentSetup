# mcp_server.py
from mcp.server.fastmcp import FastMCP


# Create an MCP server
mcp = FastMCP("AutoAgent")


@mcp.tool()
def business_object() -> str:
    """Access Fusion database business object."""
    return "Business object accessed"

@mcp.tool()
def external_rest(auth_token: str, url: str) -> str:
    """Connect to external REST API with auth."""
    return f"Fetched data from {url} using token {auth_token}"

@mcp.tool()
def document_tool(document_link: str) -> str:
    """Upload document for grounding or Q&A."""
    return f"Document added from {document_link}"

@mcp.tool()
def deeplink_tool() -> str:
    """Create Fusion deeplink."""
    return "Deeplink created"

@mcp.tool()
def calculator_tool(expression: str) -> str:
    """Perform basic math calculation."""
    return f"Result of {expression}"

@mcp.tool()
def email_tool(recipient: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {recipient} with subject '{subject}'"

@mcp.tool()
def user_context_tool() -> str:
    """Get user context information."""
    return "User: test_user_123, Role: admin"

@mcp.tool()
def topic_creator(topic_name: str, description: str) -> str:
    """Create a topic for the agent."""
    return f"Topic '{topic_name}' created: {description}"



if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')