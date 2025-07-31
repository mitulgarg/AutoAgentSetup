# client/mcp_client.py

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
        if not server_script_path.endswith((".py", ".js")):
            raise ValueError("Expected server script to be .py or .js")

        command = "python" if server_script_path.endswith(".py") else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path])

        # Start MCP server as subprocess and connect via stdio
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

        # Start client session
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # Print available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\n✅ Connected. Tools available:", [t.name for t in tools])

    async def process_query(self, query: str) -> str:
        """Send user query to OpenAI and handle tool calls via MCP."""
        messages = [{"role": "user", "content": query}]
        tools_response = await self.session.list_tools()

        # Convert MCP tools to OpenAI function spec
        functions = [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            } for tool in tools_response.tools
        ]

        while True:
            # Send to OpenAI
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                functions=functions,
                function_call="auto"
            )

            message = response.choices[0].message

            print(message)

            # Tool call requested
            if message.function_call:
                tool_name = message.function_call.name
                tool_args = json.loads(message.function_call.arguments)

                # Call tool via MCP
                tool_result = await self.session.call_tool(tool_name, tool_args)

                # Append tool call + result to chat history
                messages.append(message.model_dump())
                messages.append({
                    "role": "function",
                    "name": tool_name,
                    "content": tool_result.content
                })
            else:
                return message.content
            

    async def chat_loop(self):
        """REPL loop to interact with agent."""
        print("\n🤖 Agent is ready! Ask your question (type 'quit' to exit).")
        while True:
            try:
                query = input("\n> ").strip()
                if query.lower() in {"quit", "exit"}:
                    break
                response = await self.process_query(query)
                print("\n💬", response)
            except Exception as e:
                print("❌ Error:", str(e))

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client/mcp_client.py path/to/mcp_server.py")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect(sys.argv[1])
        print("MCP SERVER - "+ sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
