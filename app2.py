import streamlit as st
import subprocess
import json
import os
import sys
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === Setup ===
UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def run_mcp_query(user_query):
    """Run a complete query through the MCP client with OpenAI"""
    
    # Create a temporary script that mimics your mcp_client.py functionality
    script_content = f'''
import asyncio
import json
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI API client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(self, server_script_path: str):
        """Connects to the MCP server via stdio subprocess."""
        command = "python"
        server_params = StdioServerParameters(command=command, args=[server_script_path])

        # Start MCP server as subprocess and connect via stdio
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

        # Start client session
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

    async def process_query(self, query: str) -> str:
        """Send user query to OpenAI and handle tool calls via MCP."""
        messages = [{{"role": "user", "content": query}}]
        tools_response = await self.session.list_tools()

        # Convert MCP tools to OpenAI function spec
        functions = [
            {{
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }} for tool in tools_response.tools
        ]

        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Send to OpenAI
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                functions=functions,
                function_call="auto"
            )

            message = response.choices[0].message

            # Tool call requested
            if message.function_call:
                tool_name = message.function_call.name
                tool_args = json.loads(message.function_call.arguments)

                # Call tool via MCP
                tool_result = await self.session.call_tool(tool_name, tool_args)

                # Append tool call + result to chat history
                messages.append(message.model_dump())
                messages.append({{
                    "role": "function",
                    "name": tool_name,
                    "content": tool_result.content[0].text if tool_result.content else "Tool executed successfully"
                }})
            else:
                return message.content
        
        return "Max iterations reached"

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        await client.connect("mcp_server.py")
        response = await client.process_query("{user_query}")
        print("RESPONSE_START")
        print(response)
        print("RESPONSE_END")
    except Exception as e:
        print("ERROR_START")
        print(str(e))
        print("ERROR_END")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    try:
        # Write temporary script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        # Execute the script
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Clean up
        os.unlink(temp_script)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            # Extract response between markers
            if "RESPONSE_START" in output and "RESPONSE_END" in output:
                start_idx = output.find("RESPONSE_START") + len("RESPONSE_START")
                end_idx = output.find("RESPONSE_END")
                response = output[start_idx:end_idx].strip()
                return response, None
            else:
                return output, None
        else:
            error_output = result.stderr.strip()
            if "ERROR_START" in error_output:
                start_idx = error_output.find("ERROR_START") + len("ERROR_START")
                end_idx = error_output.find("ERROR_END")
                if end_idx > start_idx:
                    error = error_output[start_idx:end_idx].strip()
                else:
                    error = error_output
            else:
                error = error_output
            return None, error
            
    except subprocess.TimeoutExpired:
        return None, "Query timed out (60 seconds)"
    except Exception as e:
        return None, str(e)

def upload_document_via_mcp(file_path, file_name):
    """Upload document using MCP document tool"""
    try:
        # Read file content
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            file_content = f.read()
        
        # Create upload query
        upload_query = f"Please upload this document using the document tool. File name: {{file_name}}, Content: {{file_content[:1000]}}{'...' if len(file_content) > 1000 else ''}"
        
        # Use the MCP query system to upload
        response, error = run_mcp_query(f"Upload a document with file_name='{file_name}' and file_content containing: {file_content[:500]}...")
        
        return response, error
        
    except Exception as e:
        return None, str(e)

# === Streamlit UI ===
st.set_page_config(page_title="Auto Agent with Full MCP", layout="wide")
st.title("🧠 Auto Agent with Full MCP Integration")
st.caption("Full integration with OpenAI and MCP tools")

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ OpenAI API key not found! Please set OPENAI_API_KEY in your .env file")
    st.stop()

# === Initialize session state ===
if "messages" not in st.session_state:
    st.session_state.messages = []

# === Two column layout ===
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Chat Interface")
    
    # === Display messages ===
    for role, msg in st.session_state.messages:
        with st.chat_message(role):
            st.write(msg)
    
    # === Chat input ===
    if query := st.chat_input("Ask anything - I can help with external REST APIs, document RAG, calculations, and more!"):
        if query.strip():
            # Add user message
            st.session_state.messages.append(("user", query))
            
            # Show user message
            with st.chat_message("user"):
                st.write(query)
            
            # Process and show response
            with st.chat_message("assistant"):
                with st.spinner("Processing with OpenAI + MCP tools..."):
                    try:
                        response, error = run_mcp_query(query)
                        
                        if response and not error:
                            st.write(response)
                            st.session_state.messages.append(("assistant", response))
                        else:
                            error_msg = f"Error: {{error or 'Unknown error'}}"
                            st.error(error_msg)
                            st.session_state.messages.append(("assistant", error_msg))
                            
                    except Exception as e:
                        error_msg = f"Exception: {{str(e)}}"
                        st.error(error_msg)
                        st.session_state.messages.append(("assistant", error_msg))

with col2:
    st.header("Tools & Actions")
    
    # === Upload file section ===
    with st.expander("📄 Upload Document", expanded=True):
        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt", "docx", "md", "py", "json"])
        
        if uploaded_file is not None:
            # Save uploaded file
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Upload via MCP
            if st.button(f"Upload {{uploaded_file.name}}", key=f"upload_{{uploaded_file.name}}"):
                with st.spinner(f"Uploading {{uploaded_file.name}}..."):
                    try:
                        response, error = upload_document_via_mcp(file_path, uploaded_file.name)
                        
                        if response and not error:
                            st.success(f"✅ {{response}}")
                        else:
                            st.error(f"❌ Upload failed: {{error}}")
                            
                    except Exception as e:
                        st.error(f"❌ Upload exception: {{str(e)}}")
    
    # === Quick actions ===
    st.subheader("Quick Actions")
    
    if st.button("🧮 Test Calculator", key="calc_test"):
        with st.spinner("Testing calculator..."):
            response, error = run_mcp_query("Calculate 15 * 8 + 23")
            if response:
                st.success(response)
            else:
                st.error(f"Error: {{error}}")
    
    if st.button("👤 Get User Context", key="user_test"):
        with st.spinner("Getting user context..."):
            response, error = run_mcp_query("Get the current user context information")
            if response:
                st.success(response)
            else:
                st.error(f"Error: {{error}}")
    
    if st.button("📧 Test Email Tool", key="email_test"):
        with st.spinner("Testing email tool..."):
            response, error = run_mcp_query("Send a test email to admin@example.com with subject 'Test' and body 'This is a test email'")
            if response:
                st.success(response)
            else:
                st.error(f"Error: {{error}}")
    
    if st.button("🔗 Create Deeplink", key="deeplink_test"):
        with st.spinner("Creating deeplink..."):
            response, error = run_mcp_query("Create a deeplink for a document with ID 12345")
            if response:
                st.success(response)
            else:
                st.error(f"Error: {{error}}")
    
    if st.button("📋 List Documents", key="list_docs"):
        with st.spinner("Listing documents..."):
            response, error = run_mcp_query("List all uploaded documents")
            if response:
                st.success(response)
            else:
                st.error(f"Error: {{error}}")
    
    # === Sample queries ===
    st.subheader("Example Queries")
    st.write("Try asking:")
    st.code("""
• "Help me set up an external REST API connection with authentication"
• "Create a RAG system for document Q&A"
• "Calculate the compound interest for $1000 at 5% for 3 years"
• "Send an email to the team about the project update"
• "Create a deeplink to the financial reports"
• "What documents have been uploaded?"
    """)
    
    # === Status info ===
    st.subheader("System Status")
    api_key_status = "✅ Set" if os.getenv("OPENAI_API_KEY") else "❌ Missing"
    st.write(f"OpenAI API Key: {{api_key_status}}")
    st.write(f"MCP Server: mcp_server.py")
    st.write(f"Upload Directory: {{UPLOAD_DIR}}")