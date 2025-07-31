@echo off
REM --- Configuration ---
SET "MCP_SERVER_PORT=8001"
SET "MCP_CLIENT_PORT=8000"

REM --- Cleanup Function ---
REM This function will be called when the script is interrupted (e.g., Ctrl+C)
:cleanup
echo.
echo Stopping all services...
REM Taskkill by PID is more reliable than by window title for Uvicorn/npm
IF EXIST "%TEMP%\mcp_server_pid.txt" (
    FOR /F %%i IN (%TEMP%\mcp_server_pid.txt) DO (
        taskkill /PID %%i /F >nul 2>&1
    )
    DEL "%TEMP%\mcp_server_pid.txt"
)
IF EXIST "%TEMP%\mcp_client_pid.txt" (
    FOR /F %%i IN (%TEMP%\mcp_client_pid.txt) DO (
        taskkill /PID %%i /F >nul 2>&1
    )
    DEL "%TEMP%\mcp_client_pid.txt"
)
REM For npm, we need to find the node process listening on port 3000
FOR /F "tokens=5" %%p IN ('netstat -ano ^| findstr :3000') DO (
    taskkill /PID %%p /F >nul 2>&1
)
echo All services stopped.
exit /b 0

REM Set up Ctrl+C handler
REM On Windows, Ctrl+C directly terminates the script and its children in a command prompt.
REM We simulate trap by putting cleanup at the end and relying on direct termination or manual call.
REM For background processes, we need to explicitly kill them.

echo Starting MCP Server...
REM Start uvicorn in a new console window (START "Title" /B for background, /MIN for minimized)
REM We use `python -m uvicorn` as a robust way to run from current environment
start "MCP Server" /B python -m uvicorn MCP.mcp_server.main:app --host 0.0.0.0 --port %MCP_SERVER_PORT% --reload
REM Find the PID of the last started Python process (assuming it's Uvicorn)
FOR /F "tokens=2" %%p IN ('tasklist /nh /fi "imagename eq python.exe" ^| findstr /v "cmd.exe"') DO (
    SET /A "MCP_SERVER_PID=%%p"
    GOTO :SERVER_PID_FOUND
)
:SERVER_PID_FOUND
IF DEFINED MCP_SERVER_PID (
    ECHO %MCP_SERVER_PID% > "%TEMP%\mcp_server_pid.txt"
    echo MCP Server started with PID: %MCP_SERVER_PID% on http://localhost:%MCP_SERVER_PORT%
) ELSE (
    echo WARNING: Could not determine MCP Server PID. Manual cleanup might be needed.
)

REM Give the server a moment to start up
timeout /t 3 /nobreak >nul

echo Starting MCP Client (API Gateway)...
start "MCP Client" /B python -m uvicorn MCP.mcp_client.main:app --host 0.0.0.0 --port %MCP_CLIENT_PORT% --reload
REM Find the PID of the last started Python process (assuming it's the second Uvicorn)
REM We need to be careful to get the *new* one, not the server's.
REM A simple way is to find the process *not* in the server's PID file.
SET "MCP_CLIENT_PID="
FOR /F "tokens=2" %%p IN ('tasklist /nh /fi "imagename eq python.exe" ^| findstr /v "cmd.exe"') DO (
    SET "CURRENT_PID=%%p"
    SET "IS_SERVER_PID="
    IF EXIST "%TEMP%\mcp_server_pid.txt" (
        FOR /F %%s IN (%TEMP%\mcp_server_pid.txt) DO (
            IF "%%s"=="!CURRENT_PID!" SET "IS_SERVER_PID=1"
        )
    )
    IF NOT DEFINED IS_SERVER_PID (
        SET "MCP_CLIENT_PID=!CURRENT_PID!"
        GOTO :CLIENT_PID_FOUND
    )
)
:CLIENT_PID_FOUND
IF DEFINED MCP_CLIENT_PID (
    ECHO %MCP_CLIENT_PID% > "%TEMP%\mcp_client_pid.txt"
    echo MCP Client started with PID: %MCP_CLIENT_PID% on http://localhost:%MCP_CLIENT_PORT%
) ELSE (
    echo WARNING: Could not determine MCP Client PID. Manual cleanup might be needed.
)

REM Give the client a moment to start up
timeout /t 3 /nobreak >nul

echo Starting Frontend (React App)...
REM Navigate to the frontend directory and run npm start
REM We use 'start "" /D' to run npm in its own window, allowing it to output logs
start "Frontend" /D "frontend" npm start
REM npm start typically starts a Node.js process; we find it by the port it listens on (3000)
REM The actual PID finding for npm is tricky due to child processes.
REM We'll rely on the cleanup function's port-based kill for npm.
echo Frontend started (usually on http://localhost:3000)

echo.
echo All services are running.
echo To stop them, close this command prompt window, or press Ctrl+C multiple times if in the same window.
echo (For more reliable shutdown, you might need to manually close the new Uvicorn/Node.js windows).

REM Keep the script running (and its associated command window open)
pause >nul

REM When the pause is dismissed (or window closed), call cleanup directly
GOTO :cleanup
