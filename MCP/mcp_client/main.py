# mcp_client/main.py
import os
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import httpx # For making HTTP requests to the mcp_server
from fastapi.middleware.cors import CORSMiddleware
import inspect # For inspecting signatures for LLM context

# --- Setup ---
load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"]) # LLM setup is now here
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

# --- Configuration ---
# The MCP_SERVER_BASE_URL points to where the tool definitions are served
MCP_SERVER_BASE_URL = os.getenv("MCP_SERVER_BASE_URL", "http://localhost:8001")

# --- Pydantic Models ---
class PlanRequest(BaseModel):
    goal: str

class PlanResponse(BaseModel):
    planned_tools: List[str]

class FinalizeRequest(BaseModel):
    agent_name: str
    description: str
    goal: str
    configured_tools: List[Dict[str, Any]]

class FinalConfigResponse(BaseModel):
    agent_name: str
    description: str
    topic: str
    tools: List[Dict[str, Any]]

class ToolMetadata(BaseModel):
    tool_name: str
    description: str
    parameters: List[Dict[str, Any]] # List of {name: str, type: str, optional: bool}

class ToolsMetadataResponse(BaseModel):
    tools: List[ToolMetadata]

# Cache for tool metadata to avoid repeated HTTP calls
_cached_tools_metadata: Optional[Dict[str, Dict[str, Any]]] = None

async def _get_all_tools_metadata() -> Dict[str, Dict[str, Any]]:
    """Fetches and caches tool metadata from the MCP Tool Definitions Server."""
    global _cached_tools_metadata
    if _cached_tools_metadata is not None:
        return _cached_tools_metadata

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{MCP_SERVER_BASE_URL}/get-tools-metadata")
            response.raise_for_status()
            data = response.json()
            
            metadata_map = {}
            for tool_info in data.get("tools", []):
                metadata_map[tool_info["tool_name"]] = tool_info
            _cached_tools_metadata = metadata_map
            return metadata_map
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Error fetching tool metadata from MCP Server: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Cannot connect to MCP Tool Definitions Server: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching tool metadata: {e}")


# --- Core Logic Functions (now with LLM calls) ---

async def generate_plan_logic(goal: str) -> List[str]:
    """Generates a list of tool names based on the user's goal using LLM."""
    
    all_tools_metadata = await _get_all_tools_metadata()
    available_tool_names = list(all_tools_metadata.keys())

    planning_prompt = f"""
    Based on the user's goal, identify the necessary tools in the correct order of execution.
    Only use tools from the provided list. If no tool is suitable, respond with "None".
    Present the list of tool names as a simple, comma-separated string (e.g., "tool1, tool2").

    Goal: "{goal}"
    Available Tools: {', '.join(available_tool_names)}
    """
    try:
        planning_model = genai.GenerativeModel('gemini-2.5-flash')
        response = planning_model.generate_content(planning_prompt)
        raw_plan = response.text.strip().lower()

        if raw_plan == "none" or not raw_plan:
            return []

        planned_tools = [tool.strip() for tool in raw_plan.split(',') if tool.strip()]
        
        # Validate that the planned tools actually exist
        valid_tools = [tool for tool in planned_tools if tool in available_tool_names]
        
        if not valid_tools and planned_tools:
             raise ValueError(f"LLM suggested unknown tools: {', '.join(planned_tools)}. Please refine your goal or available tools.")
        
        return valid_tools
    except Exception as e:
        print(f"Error in generate_plan_logic: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {e}")

async def generate_topic_logic(goal: str, planned_tools: List[str]) -> str:
    """Generates the natural language workflow description (the 'topic') using LLM."""
    
    if not planned_tools:
        return "No specific workflow logic required as no tools were planned."

    all_tools_metadata = await _get_all_tools_metadata()

    tool_descriptions = []
    for tool_name in planned_tools:
        tool_info = all_tools_metadata.get(tool_name)
        if tool_info:
            params_str = ", ".join([f"{p['name']}:{p['type']}" for p in tool_info['parameters']])
            tool_descriptions.append(f"- {tool_name} ({tool_info['description']}) Parameters: [{params_str}]")

    logic_generation_prompt = f"""
    Based on the user's goal and the chosen tools, write a concise, natural language description of how these tools should work together to achieve the goal. This description will be the agent's core operational logic or "topic" in an AI Agent Studio.

    Focus on the sequence and dependencies between the tools. If a tool has parameters, mention how they might be derived or what information the user needs to provide for them.

    User's Goal: "{goal}"
    Chosen Tools and their descriptions/parameters:
    {tool_descriptions}

    Example Topic:
    "When the user wants to calculate and then send an email:
    1. First, use the `calculator_tool` to perform the calculation, getting the `expression` from the user.
    2. Then, take the `result` from the calculator.
    3. Finally, use the `email_tool` to send an email to a `recipient`, potentially including the `result` in the `body` of the email."
    """
    try:
        logic_model = genai.GenerativeModel('gemini-2.5-flash')
        response = logic_model.generate_content(logic_generation_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error in generate_topic_logic: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate topic logic: {e}")

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Agent Builder Client (with LLM) API is running."}

@app.post("/generate-plan", response_model=PlanResponse)
async def get_plan(request: PlanRequest):
    """
    Receives the user's goal and returns a list of planned tools using LLM.
    """
    planned_tools = await generate_plan_logic(request.goal)
    return PlanResponse(planned_tools=planned_tools)

@app.post("/finalize-agent", response_model=FinalConfigResponse)
async def finalize_agent(request: FinalizeRequest):
    """
    Receives all the final data, generates the topic using LLM, and creates the complete JSON config.
    """
    planned_tool_names = [t['tool_name'] for t in request.configured_tools]
    topic_text = await generate_topic_logic(request.goal, planned_tool_names)

    final_config = {
        "agent_name": request.agent_name,
        "description": request.description,
        "topic": topic_text,
        "tools": request.configured_tools,
    }

    return FinalConfigResponse(**final_config)

@app.get("/get-tools-metadata", response_model=ToolsMetadataResponse)
async def get_tools_metadata():
    """
    Forwards the request to MCP Server to get metadata about available tools.
    This allows the frontend to dynamically render parameter forms.
    """
    # This endpoint still proxies the request to the mcp_server,
    # but the _get_all_tools_metadata() function caches the result
    # to avoid repeated HTTP calls during LLM generation.
    metadata_map = await _get_all_tools_metadata()
    return ToolsMetadataResponse(tools=list(metadata_map.values()))