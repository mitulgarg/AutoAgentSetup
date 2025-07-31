#!/bin/bash

# --- Configuration ---
# Define ports for the backend services
MCP_SERVER_PORT=8001
MCP_CLIENT_PORT=8000

# --- Cleanup Function ---
# This function will be called when the script is interrupted (e.g., Ctrl+C)
cleanup() {
    echo -e "\nStopping all services..."
    # Killing processes using their PIDs
    kill "$MCP_SERVER_PID" 2>/dev/null
    kill "$MCP_CLIENT_PID" 2>/dev/null
    kill "$FRONTEND_PID" 2>/dev/null
    echo "All services stopped."
    exit 0
}

# Trap Ctrl+C (SIGINT) and call the cleanup function
trap cleanup SIGINT

echo "Starting MCP Server..."
# Run mcp_server in the background
# The path now includes 'MCP' as the script is outside it
uvicorn MCP.mcp_server.main:app --host 0.0.0.0 --port "$MCP_SERVER_PORT" --reload &
MCP_SERVER_PID=$!
echo "MCP Server started with PID: $MCP_SERVER_PID on http://localhost:$MCP_SERVER_PORT"

# Give the server a moment to start up
sleep 3

echo "Starting MCP Client (API Gateway)..."
# Run mcp_client in the background
# The path now includes 'MCP'
uvicorn MCP.mcp_client.main:app --host 0.0.0.0 --port "$MCP_CLIENT_PORT" --reload &
MCP_CLIENT_PID=$!
echo "MCP Client started with PID: $MCP_CLIENT_PID on http://localhost:$MCP_CLIENT_PORT"

# Give the client a moment to start up
sleep 3

echo "Starting Frontend (React App)..."
# Navigate to the frontend directory and run npm start in the background
# The path is directly 'frontend' as the script is its sibling
(cd frontend/agent-frontend && npm start) &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID (usually on http://localhost:3000)"

echo -e "\nAll services are running. Press Ctrl+C to stop all of them."

# Keep the script running in the foreground until interrupted
wait