import os
import json
import base64 # Import for handling binary file content
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.adk.agents import Agent
from dotenv import load_dotenv
from typing import List, Dict, Any, Callable, Optional # Import Optional
from pydantic import PrivateAttr

load_dotenv()

# --- Tool Blueprints (Improved) ---

# ... (business_object, document_tool, etc. are unchanged) ...

# ✨ IMPROVEMENT: Made auth_token optional to handle APIs with no authentication.
def external_rest(url: str, auth_token: Optional[str] = None) -> str:
    """Connect to an external REST API. An authentication token is optional."""
    pass

# ... (Other tool definitions are unchanged) ...
def business_object() -> str:
    """Access a business object within the Fusion database."""
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

def email_tool(recipient: str, subject: str, body: str) -> str:
    """Send an email to a specified recipient."""
    pass

def user_context_tool() -> str:
    """Get information about the current user, such as ID, role, and department."""
    pass

def topic_creator(topic_name: str, description: str) -> str:
    """Create a new discussion topic for the agent."""
    pass

def list_uploaded_documents() -> str:
    """List all documents that have been previously uploaded."""
    pass

def finalize_configuration(agent_name: str, description: str) -> str:
    """
    Generates the final JSON configuration file for the new agent.
    This tool should only be called when the user has finished adding all desired tools.
    """
    return "Configuration finalization initiated."


# --- Orchestrator Agent ---

class AgentBuilder(Agent):
    """
    An agent that helps users build a configuration for another agent
    by asking questions to determine the right tools and parameters.
    """
    _model: GenerativeModel = PrivateAttr()
    _configured_tools: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _conversation_history: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _available_tools: List[Callable] = PrivateAttr(default_factory=list)

    def __init__(self, model: GenerativeModel):
        super().__init__(
            name="AgentBuilder",
            description="An agent that helps users build a configuration for another agent."
        )
        self._model = model
        self._configured_tools = []
        self._conversation_history = []
        self._available_tools = [
            business_object, external_rest, document_tool,
            deeplink_tool, calculator_tool, email_tool,
            user_context_tool, topic_creator, list_uploaded_documents,
            finalize_configuration
        ]

    def run(self):
        """Starts the interactive agent configuration session."""
        system_prompt = """
        You are an 'Agent Builder' assistant. Your job is to help a user create a JSON configuration for an Oracle AI Agent by interactively asking questions.
        Your capabilities are defined by a set of available tools. Your goal is to understand the user's needs and determine which tools to use and what parameters are required for each.
        Follow these rules:
        1.  Analyze the user's request to identify which tool is needed.
        2.  If you have all the necessary parameters for a tool, make a function call. My system will intercept this call and add it to the configuration.
        3.  If you are missing information for a tool's parameters (e.g., a URL), you MUST ask the user a clear, direct question to get the missing information. Do NOT make up placeholders.
        4.  For the `document_tool`, you only need the `file_name` parameter. My system will handle getting the actual file content from the user.
        5.  For the `external_rest` tool, the `auth_token` is optional. Do not ask for it unless the user mentions authentication.
        6.  After adding a tool to the configuration, confirm with the user and ask what to do next.
        7.  When the user indicates they are finished adding tools, call the `finalize_configuration` function. You will need to ask for a name and description for the agent.
        """
        self._model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=self._available_tools,
            system_instruction=system_prompt
        )
        chat = self._model.start_chat(history=[])

        print("🤖 Hello! I'm the Agent Builder. Describe what task you'd like to automate.")
        print("-" * 30)

        while True:
            user_input = input("👤 You: ")
            if user_input.lower() in ["exit", "quit"]:
                print("🤖 Goodbye!")
                break
            
            response = chat.send_message(user_input)
            response_part = response.candidates[0].content.parts[0]

            if response_part.function_call:
                fc = response_part.function_call
                tool_name = fc.name
                tool_args = {key: value for key, value in fc.args.items()}

                if tool_name == "finalize_configuration":
                    self._generate_json_file(tool_args['agent_name'], tool_args['description'])
                    break
                
                elif tool_name == "document_tool":
                    self._handle_document_tool(tool_args)
                
                else:
                    tool_config = {"tool_name": tool_name, "parameters": tool_args}
                    self._configured_tools.append(tool_config)
                    msg = f"✅ OK, I've added the `{tool_name}` tool to the configuration. What's next?"
                    print(f"🤖 Agent Builder: {msg}")

            else:
                print(f"🤖 Agent Builder: {response_part.text}")

    def _handle_document_tool(self, tool_args: dict):
        """Prompts user for a local file path and configures the document tool."""
        try:
            file_name = tool_args.get('file_name', 'document.txt')
            local_path = input(f"🤖 Please provide the local file path for '{file_name}': ")
            
            if os.path.exists(local_path):
                # ✨ IMPROVEMENT: Read the file in binary mode ("rb") to avoid crashing.
                with open(local_path, "rb") as f:
                    binary_content = f.read()
                
                # For JSON compatibility, it's best to encode binary data in Base64.
                # This ensures any file type can be handled.
                encoded_content = base64.b64encode(binary_content).decode('utf-8')

                tool_config = {
                    "tool_name": "document_tool",
                    "parameters": {
                        "file_name": os.path.basename(local_path),
                        "file_content": encoded_content,
                        "encoding": "base64" # Add encoding info
                    }
                }
                self._configured_tools.append(tool_config)
                print(f"🤖 Agent Builder: ✅ OK, I've successfully processed and configured the document '{os.path.basename(local_path)}'. What's next?")
            else:
                print(f"🤖 Agent Builder: ❌ Error: File not found at '{local_path}'. Please try configuring the tool again.")
        except Exception as e:
            print(f"🤖 Agent Builder: ❌ An error occurred while processing the file: {e}")

    def _generate_json_file(self, agent_name: str, description: str):
        """Saves the final configuration to a JSON file."""
        config = {
            "agent_name": agent_name,
            "description": description,
            "configured_tools": self._configured_tools
        }
        file_name = f"{agent_name.replace(' ', '_').lower()}_config.json"
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            print("-" * 30)
            print(f"✅ Configuration successfully saved to '{file_name}'!")
            print(json.dumps(config, indent=4))
            print("-" * 30)
        except Exception as e:
            print(f"❌ Error saving configuration: {str(e)}")


if __name__ == "__main__":
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model_instance = genai.GenerativeModel('gemini-2.5-flash')
        
        builder = AgentBuilder(model=model_instance)
        builder.run()

    except (TypeError, KeyError):
        print("❌ Error: GOOGLE_API_KEY environment variable not set.")
        print("Please set it by creating a .env file or running: export GOOGLE_API_KEY='your_api_key_here'")