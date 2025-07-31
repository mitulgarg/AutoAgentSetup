import streamlit as st
import asyncio
import os
import json
import threading
import concurrent.futures
from client.mcp_client import MCPClient

# === Setup ===
UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# === Async helper functions ===
import threading
import concurrent.futures

def run_async(coro):
    """Run async function in a separate thread to avoid event loop conflicts"""
    def run_in_thread():
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    # Run in a separate thread to avoid conflicts with Streamlit's event loop
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result(timeout=30)  # 30 second timeout

# === Initialize client connection ===
async def initialize_client():
    """Initialize MCP client connection"""
    try:
        client = MCPClient()
        await client.connect("mcp_server.py")
        return client, None
    except Exception as e:
        return None, str(e)

# === Send message to agent ===
async def process_user_query(client, query):
    """Process user query through MCP client"""
    try:
        print(f"Processing query: {query}")  # Debug log
        response = await client.process_query(query)
        print(f"Got response: {response}")  # Debug log
        return response, None
    except Exception as e:
        print(f"Error in process_user_query: {str(e)}")  # Debug log
        return None, str(e)

# === Upload document via MCP ===
async def upload_document_via_mcp(client, file_path, file_name):
    """Upload document using MCP tool"""
    try:
        # Read file content
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            file_content = f.read()
        
        # Call MCP tool
        tool_result = await client.session.call_tool(
            "document_tool", 
            {"file_name": file_name, "file_content": file_content}
        )
        return tool_result.content[0].text if tool_result.content else "Upload successful", None
    except Exception as e:
        return None, str(e)

# === Streamlit UI ===
st.set_page_config(page_title="Auto Agent", layout="centered")
st.title("🧠 Auto Agent")
st.caption("Ask questions or upload documents.")

# === Initialize session state ===
if "messages" not in st.session_state:
    st.session_state.messages = []

if "client" not in st.session_state:
    st.session_state.client = None
    st.session_state.connection_error = None
    
    # Try to initialize client
    with st.spinner("Connecting to MCP server..."):
        try:
            client, error = run_async(initialize_client())
            if client:
                st.session_state.client = client
                st.success("✅ Connected to MCP server!")
            else:
                st.session_state.connection_error = error
                st.error(f"❌ Failed to connect: {error}")
        except Exception as e:
            st.session_state.connection_error = str(e)
            st.error(f"❌ Connection error: {e}")

# === Display connection status ===
if st.session_state.client is None:
    st.error("⚠️ MCP client not connected. Please restart the app.")
    if st.button("Retry Connection"):
        st.rerun()
else:
    # === Message display ===
    for role, msg in st.session_state.messages:
        with st.chat_message(role):
            st.write(msg)

    # === Chat input ===
    if query := st.chat_input("Ask a question"):
        if query.strip():
            # Add user message immediately
            st.session_state.messages.append(("user", query))
            
            # Show user message
            with st.chat_message("user"):
                st.write(query)
            
            # Process query and get response
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Thinking..."):
                        response, error = run_async(process_user_query(st.session_state.client, query))
                        
                        if response:
                            st.write(response)
                            st.session_state.messages.append(("assistant", response))
                        else:
                            error_msg = f"Error: {error}"
                            st.error(error_msg)
                            st.session_state.messages.append(("assistant", error_msg))
                except concurrent.futures.TimeoutError:
                    error_msg = "Request timed out. Please try again."
                    st.error(error_msg)
                    st.session_state.messages.append(("assistant", error_msg))
                except Exception as e:
                    error_msg = f"Unexpected error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append(("assistant", error_msg))

    # === Upload file section ===
    with st.expander("📄 Upload Document"):
        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt", "docx", "md"])
        
        if uploaded_file is not None:
            # Save uploaded file
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Upload via MCP
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                result, error = run_async(
                    upload_document_via_mcp(st.session_state.client, file_path, uploaded_file.name)
                )
                
                if result:
                    st.success(f"✅ {result}")
                else:
                    st.error(f"❌ Upload failed: {error}")

# === Sidebar with connection info ===
with st.sidebar:
    st.header("Connection Status")
    if st.session_state.client:
        st.success("🟢 MCP Client Connected")
        if st.button("Disconnect & Reconnect"):
            # Clear client and force reconnection
            if st.session_state.client:
                run_async(st.session_state.client.cleanup())
            st.session_state.client = None
            st.rerun()
    else:
        st.error("🔴 MCP Client Disconnected")
        
    st.header("Available Tools")
    if st.session_state.client and st.session_state.client.session:
        try:
            tools_response = run_async(st.session_state.client.session.list_tools())
            for tool in tools_response.tools:
                st.text(f"• {tool.name}")
        except:
            st.text("Could not fetch tools")