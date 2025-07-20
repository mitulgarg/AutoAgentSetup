from mcp.server.fastmcp import FastMCP
import os
import json

# Create an MCP server
mcp = FastMCP("AutoAgent")

@mcp.tool()
def business_object() -> str:
    """Access Fusion database business object."""
    return "Business object accessed successfully"

@mcp.tool()
def external_rest(auth_token: str, url: str) -> str:
    """Connect to external REST API with authentication."""
    return f"Successfully fetched data from {url} using authentication token"

@mcp.tool()
def document_tool(file_name: str = "", file_content: str = "") -> str:
    """Upload and process document for grounding or Q&A."""
    if not file_name or not file_content:
        return "Error: Both file_name and file_content are required"
    
    try:
        # Create documents directory if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        docs_dir = os.path.join(script_dir, "uploaded_docs")
        os.makedirs(docs_dir, exist_ok=True)
        
        # Save document
        file_path = os.path.join(docs_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        
        # Return success message with file info
        return f"✅ Document '{file_name}' successfully uploaded and saved to {file_path}. Content length: {len(file_content)} characters."
        
    except Exception as e:
        return f"❌ Error uploading document: {str(e)}"

@mcp.tool()
def deeplink_tool(resource_type: str = "default", resource_id: str = "") -> str:
    """Create Fusion deeplink for specific resource."""
    base_url = "https://fusion.example.com"
    if resource_id:
        deeplink = f"{base_url}/{resource_type}/{resource_id}"
    else:
        deeplink = f"{base_url}/{resource_type}"
    return f"✅ Deeplink created: {deeplink}"

@mcp.tool()
def calculator_tool(expression: str) -> str:
    """Perform basic math calculations safely."""
    try:
        # Only allow basic mathematical operations for security
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            return "❌ Error: Invalid characters in expression. Only numbers and +, -, *, /, (, ) are allowed."
        
        # Evaluate the expression
        result = eval(expression)
        return f"✅ Result of '{expression}' = {result}"
    
    except ZeroDivisionError:
        return "❌ Error: Division by zero"
    except Exception as e:
        return f"❌ Error calculating '{expression}': {str(e)}"

@mcp.tool()
def email_tool(recipient: str, subject: str, body: str) -> str:
    """Send an email (simulation)."""
    if not recipient or not subject:
        return "❌ Error: recipient and subject are required"
    
    return f"✅ Email sent successfully!\nTo: {recipient}\nSubject: {subject}\nBody preview: {body[:50]}{'...' if len(body) > 50 else ''}"

@mcp.tool()
def user_context_tool() -> str:
    """Get current user context information."""
    user_info = {
        "user_id": "test_user_123",
        "role": "admin",
        "department": "IT",
        "permissions": ["read", "write", "admin"],
        "session_start": "2024-01-15T10:30:00Z"
    }
    return f"✅ User Context: {json.dumps(user_info, indent=2)}"

@mcp.tool()
def topic_creator(topic_name: str, description: str = "") -> str:
    """Create a new topic for the agent to discuss."""
    if not topic_name:
        return "❌ Error: topic_name is required"
    
    topic_info = {
        "name": topic_name,
        "description": description or f"Auto-generated topic: {topic_name}",
        "created_at": "2024-01-15T10:30:00Z",
        "status": "active"
    }
    
    return f"✅ Topic '{topic_name}' created successfully!\nDetails: {json.dumps(topic_info, indent=2)}"

@mcp.tool()
def list_uploaded_documents() -> str:
    """List all uploaded documents."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        docs_dir = os.path.join(script_dir, "uploaded_docs")
        
        if not os.path.exists(docs_dir):
            return "No documents uploaded yet."
        
        files = os.listdir(docs_dir)
        if not files:
            return "No documents found in upload directory."
        
        file_list = []
        for file in files:
            file_path = os.path.join(docs_dir, file)
            size = os.path.getsize(file_path)
            file_list.append(f"📄 {file} ({size} bytes)")
        
        return "✅ Uploaded Documents:\n" + "\n".join(file_list)
        
    except Exception as e:
        return f"❌ Error listing documents: {str(e)}"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')


