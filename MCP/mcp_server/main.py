# mcp_server/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Callable
from fastapi.middleware.cors import CORSMiddleware

# Import tools and the metadata utility
from .tools import AVAILABLE_TOOLS_MAP, _get_tool_metadata_single

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Tool Metadata ---
class ToolMetadata(BaseModel):
    tool_name: str
    description: str
    parameters: List[Dict[str, Any]] # List of {name: str, type: str, optional: bool}

class ToolsMetadataResponse(BaseModel):
    tools: List[ToolMetadata]

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "MCP Tool Definitions Server is running."}

@app.get("/get-tools-metadata", response_model=ToolsMetadataResponse)
async def get_tools_metadata():
    """
    Returns metadata (name, description, parameters) for all available tools.
    This helps the client dynamically build UIs for tool configuration.
    """
    metadata = [_get_tool_metadata_single(func) for func in AVAILABLE_TOOLS_MAP.values()]
    return ToolsMetadataResponse(tools=metadata)