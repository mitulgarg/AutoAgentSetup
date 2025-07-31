import os
import json
import base64
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.adk.agents import Agent
from dotenv import load_dotenv
from typing import List, Dict, Any, Callable, Optional
from pydantic import PrivateAttr
import re

load_dotenv()

# --- Tool Blueprints ---
# (Definitions are unchanged, as they represent the FINAL agent's capabilities)
def external_rest(url: str, auth_token: Optional[str] = None) -> str:
    """Connect to an external REST API. An authentication token is optional."""
    pass

def document_tool(file_name: str) -> str:
    """Configures a document for the agent to use by providing a local file path."""
    pass

def calculator_tool(expression: str) -> str:
    """Perform a basic math calculation. Example: '(100 + 50) / 2'"""
    pass

def finalize_configuration() -> str:
    """Call this function only when all tools in the plan are configured."""
    return "Finalizing agent configuration."

# ... (other tool definitions)

# ✨ FIX 1: Define which tools don't need user input during configuration.
TOOLS_REQUIRING_NO_PARAMS = ["calculator_tool", "user_context_tool", "list_uploaded_documents"]


class AgentBuilder(Agent):
    _model: GenerativeModel = PrivateAttr()
    _configured_tools: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _available_tools: List[Callable] = PrivateAttr(default_factory=list)

    def __init__(self, model: GenerativeModel):
        super().__init__(
            name="AgentBuilder",
            description="A 'plan-and-execute' agent that builds configurations for other agents."
        )
        self._model = model
        self._configured_tools = []
        self._available_tools = [
            external_rest, document_tool, calculator_tool, finalize_configuration
        ]

    # ✨ FIX 2: Complete overhaul of the run() method for a "Plan-and-Execute" flow.
    def run(self):
        """Starts the interactive agent configuration session."""
        print("🤖 Hello! I'm the Agent Builder. Let's start by defining your new agent.")
        print("-" * 30)

        # --- Initial Definition ---
        agent_name = input("👤 What would you like to name your new agent? ")
        agent_description = input(f"👤 Great! Now, provide a brief description for '{agent_name}': ")
        initial_goal = input(f"👤 Perfect. Now, in one sentence, describe the main goal of '{agent_name}': ")
        print("-" * 30)

        # --- PHASE 1: PLANNING ---
        planning_prompt = f"""
        Based on the user's goal, identify the necessary tools from the available list.
        Present the list of tool names as a simple, comma-separated string. Do not add any other text.
        Goal: "{initial_goal}"
        Available Tools: {', '.join([tool.__name__ for tool in self._available_tools if tool.__name__ != 'finalize_configuration'])}
        """
        planning_model = genai.GenerativeModel('gemini-2.5-flash')
        response = planning_model.generate_content(planning_prompt)
        
        # Clean up the LLM response to get a clean list of tool names
        tool_names_str = response.text.strip()
        planned_tools = [tool.strip() for tool in re.split(r'[,\s]+', tool_names_str) if tool.strip()]

        print("🤖 Based on your goal, here is the plan:")
        for tool in planned_tools:
            print(f"   - Step: Configure `{tool}`")
        
        approval = input("🤖 Does this plan look correct? (yes/no): ")
        if approval.lower() != 'yes':
            print("🤖 Plan rejected. Please restart and describe your goal more clearly.")
            return
        
        print("-" * 30)
        print("🤖 Great! Let's execute the plan.")

        # --- PHASE 2: EXECUTION ---
        for tool_name in planned_tools:
            print(f"\n--- Configuring Step: `{tool_name}` ---")
            if tool_name in TOOLS_REQUIRING_NO_PARAMS:
                self._configured_tools.append({"tool_name": tool_name, "parameters": {}})
                print(f"✅ Automatically configured `{tool_name}` as it requires no parameters.")
                continue

            # This is the configuration loop for a single tool that needs parameters
            self._configure_single_tool(tool_name)

        print("\n" + "-" * 30)
        print("✅ All steps in the plan are complete!")
        self._generate_json_file(agent_name, agent_description)

    def _configure_single_tool(self, tool_name: str):
        """Runs a targeted conversation to configure one specific tool."""
        config_prompt = f"""
        Your current and ONLY task is to configure the `{tool_name}` tool.
        Gather all necessary parameters from the user.
        Once you have the parameters, call the function for `{tool_name}`.
        """
        config_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=[tool for tool in self._available_tools if tool.__name__ == tool_name],
            system_instruction=config_prompt
        )
        chat = config_model.start_chat(history=[])
        
        # Start the conversation
        response = chat.send_message(f"Let's configure the `{tool_name}`.")
        print(f"🤖 Agent Builder: {response.text}")

        while True:
            user_input = input("👤 You: ")
            response = chat.send_message(user_input)
            
            if response.candidates[0].content.parts[0].function_call:
                fc = response.candidates[0].content.parts[0].function_call
                tool_args = {key: value for key, value in fc.args.items()}
                
                if fc.name == "document_tool":
                    self._handle_document_tool(tool_args)
                else:
                    self._configured_tools.append({"tool_name": fc.name, "parameters": tool_args})
                
                print(f"✅ Successfully configured `{fc.name}`.")
                break # Exit loop after successful configuration
            else:
                print(f"🤖 Agent Builder: {response.text}")
    
    # _handle_document_tool and _generate_json_file methods remain the same...
    def _handle_document_tool(self, tool_args: dict):
        try:
            file_name = tool_args.get('file_name', 'document.txt')
            local_path = input(f"🤖 Please provide the local file path for '{file_name}': ").strip().strip("'\"")
            
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    binary_content = f.read()
                
                encoded_content = base64.b64encode(binary_content).decode('utf-8')

                tool_config = {
                    "tool_name": "document_tool",
                    "parameters": {
                        "file_name": os.path.basename(local_path),
                        "file_content": encoded_content,
                        "encoding": "base64"
                    }
                }
                self._configured_tools.append(tool_config)
            else:
                print(f"❌ Error: File not found at '{local_path}'. Configuration for this tool failed.")
        except Exception as e:
            print(f"❌ An error occurred: {e}. Configuration for this tool failed.")

    def _generate_json_file(self, agent_name: str, description: str):
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