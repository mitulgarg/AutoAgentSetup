import os
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Dict, Any, Callable, Optional
from inspect import signature
import re
from fastapi.middleware.cors import CORSMiddleware

# --- Setup ---
load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000", # The default origin for Create React App
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"], # Allow all headers
)

# --- Tool Definitions and Availability ---
# ✨ FIX: All logic is now in one file. These are the blueprints for our agent.
def external_rest(url: str, auth_token: Optional[str] = None) -> str:
    """Connect to an external REST API."""
    pass

def document_tool(file_name: str) -> str:
    """Configures a document for the agent to use by providing a local file path."""
    pass

def calculator_tool() -> str:
    """Enables the calculator tool for runtime calculations."""
    pass


# ... (Other tool definitions are unchanged) ...
def business_object(link_name:str) -> str:
    """Access a business object within the Fusion OpenAPI spec in a given URL."""
    print(link_name)
    pass

def document_tool(file_name: str, file_content: str = "") -> str:
    """
    Upload a document for grounding or Q&A.
    The agent will prompt the user for a local file path to get the content.
    """
    pass

def deeplink_tool(resource_type: str, resource_id: str) -> str:
    """Create a Fusion deeplink for a specific resource type and ID."""
    pass

def calculator_tool(expression: str) -> str:
    """Perform a basic math calculation. Example: '(100 + 50) / 2'"""
    pass

def email_tool(recipient: str) -> str:
    """Send an email to a specified recipient."""
    pass

def user_context_tool() -> str:
    """Get information about the current user, such as ID, role, and department."""
    pass



def list_uploaded_documents() -> str:
    """List all documents that have been previously uploaded."""
    pass

# A dictionary to easily access tool functions by name
AVAILABLE_TOOLS_MAP = {
    "external_rest": external_rest,
    "document_tool": document_tool,
    "calculator_tool": calculator_tool,
    "email_tool":email_tool,
    "business_object":business_object
}

# --- Pydantic Models for API Data Structure ---
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

# --- Core Logic Functions (Ported from your AgentBuilder) ---
# ✨ FIX: These functions contain the logic previously in the run() method.

def generate_plan_logic(goal: str) -> List[str]:
    """Generates a list of tool names based on the user's goal."""
    planning_prompt = f"""
    Based on the user's goal, identify the necessary tools in the correct order of execution.
    Present the list of tool names as a simple, comma-separated string.
    Goal: "{goal}"
    Available Tools: {', '.join(AVAILABLE_TOOLS_MAP.keys())}
    """
    try:
        planning_model = genai.GenerativeModel('gemini-2.5-flash')
        response = planning_model.generate_content(planning_prompt)
        planned_tools = [tool.strip() for tool in response.text.strip().split(',') if tool.strip()]
        # Validate that the planned tools actually exist
        valid_tools = [tool for tool in planned_tools if tool in AVAILABLE_TOOLS_MAP]
        return valid_tools
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {e}")

def generate_topic_logic(goal: str, planned_tools: List[str]) -> str:
    """Generates the natural language workflow description (the 'topic')."""
    logic_generation_prompt = f"""
    Based on the user's goal and the chosen tools, write a concise, natural language description of how the tools should work together.
    This description will be the agent's core operational logic or "topic".
    User's Goal: "{goal}"
    Chosen Tools: {', '.join(planned_tools)}
    Example: "When the user asks a question, first use the calculator_tool. Then, take the result from the calculator and use it as the 'query' parameter for the external_rest tool."
    """
    try:
        logic_model = genai.GenerativeModel('gemini-2.5-flash')
        response = logic_model.generate_content(logic_generation_prompt)
        return response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate topic logic: {e}")

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Agent Builder API is running."}

@app.post("/generate-plan", response_model=PlanResponse)
async def get_plan(request: PlanRequest):
    """
    Receives the user's goal and returns a list of planned tools.
    """
    planned_tools = generate_plan_logic(request.goal)
    return PlanResponse(planned_tools=planned_tools)

@app.post("/finalize-agent", response_model=FinalConfigResponse)
async def finalize_agent(request: FinalizeRequest):
    """
    Receives all the final data and generates the complete JSON config.
    """
    topic_text = generate_topic_logic(request.goal, [t['tool_name'] for t in request.configured_tools])

    final_config = {
        "agent_name": request.agent_name,
        "description": request.description,
        "topic": topic_text,
        "tools": request.configured_tools,
    }

    # In a real app, you might save this to a database or file.
    # Here, we just return it to the frontend.
    return FinalConfigResponse(**final_config)