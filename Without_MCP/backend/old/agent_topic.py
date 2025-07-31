import os
import json
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.adk.agents import Agent
from dotenv import load_dotenv
from typing import List, Dict, Any, Callable, Optional
from pydantic import PrivateAttr
import re
from inspect import signature

load_dotenv()

# --- Tool Blueprints (Simplified for this workflow) ---
def external_rest(url: str, auth_token: Optional[str] = None) -> str:
    """Connect to an external REST API."""
    pass

def document_tool(file_name: str) -> str:
    """Configures a document for the agent to use by providing a local file path."""
    pass

def calculator_tool() -> str:
    """Enables the calculator tool for runtime calculations."""
    pass


class AgentBuilder(Agent):
    _model: GenerativeModel = PrivateAttr()
    _configured_tools: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _available_tools: List[Callable] = PrivateAttr(default_factory=list)

    def __init__(self, model: GenerativeModel):
        super().__init__(
            name="AgentBuilder",
            description="A 'plan-and-execute' agent that builds tool workflows."
        )
        self._model = model
        self._configured_tools = []
        self._available_tools = [
            external_rest, document_tool, calculator_tool
        ]

    def run(self):
        """Starts the interactive agent configuration session."""
        print("🤖 Hello! I'm the Agent Workflow Builder.")
        print("-" * 30)

        agent_name = input("👤 What would you like to name your new agent? ")
        agent_description = input(f"👤 Great! Now, provide a brief description for '{agent_name}': ")
        initial_goal = input(f"👤 Perfect. Now, describe the workflow you want to build for '{agent_name}': ")
        print("-" * 30)

        # --- PHASE 1: PLANNING ---
        planning_prompt = f"""
        Based on the user's goal, identify the necessary tools in the correct order of execution.
        Present the list of tool names as a simple, comma-separated string.
        Goal: "{initial_goal}"
        Available Tools: {', '.join([tool.__name__ for tool in self._available_tools])}
        """
        planning_model = genai.GenerativeModel('gemini-2.5-flash')
        response = planning_model.generate_content(planning_prompt)
        planned_tools = [tool.strip() for tool in response.text.strip().split(',') if tool.strip()]

        print("🤖 Based on your goal, here is the planned workflow:")
        for i, tool in enumerate(planned_tools):
            print(f"   - Step {i+1}: `{tool}`")

        approval = input("🤖 Does this plan look correct? (yes/no): ")
        if approval.lower() != 'yes':
            print("🤖 Plan rejected. Please restart.")
            return

        print("-" * 30)
        print("🤖 Great! Let's configure the basic parameters for the planned steps.")

        # --- PHASE 2: STATIC CONFIGURATION ---
        for tool_name in planned_tools:
            self._configure_single_tool(tool_name)

        # ✨ FIX: PHASE 3 - Automatically generate the workflow logic ("Topic")
        print("\n" + "-" * 30)
        print("🤖 Generating workflow logic...")
        logic_generation_prompt = f"""
        Based on the user's goal and the chosen tools, write a concise, natural language description of how the tools should work together.
        This description will be the agent's core operational logic or "topic".
        User's Goal: "{initial_goal}"
        Chosen Tools: {', '.join(planned_tools)}
        Example: "When the user asks a question, first use the calculator_tool. Then, take the result from the calculator and use it as the 'query' parameter for the external_rest tool."
        """
        logic_model = genai.GenerativeModel('gemini-2.5-flash')
        logic_response = logic_model.generate_content(logic_generation_prompt)
        topic_text = logic_response.text.strip()
        print("🤖 Workflow logic generated.")

        print("\n" + "-" * 30)
        print("✅ Workflow configuration complete!")
        self._generate_json_file(agent_name, agent_description, topic_text)

    # ✨ FIX: This method is now much simpler.
    def _configure_single_tool(self, tool_name: str):
        """Runs a simple conversation to get static parameters for a tool."""
        print(f"\n--- Configuring Step: `{tool_name}` ---")

        tool_config = {"tool_name": tool_name, "parameters": {}}
        tool_function = next((t for t in self._available_tools if t.__name__ == tool_name), None)
        
        # Check if the tool has any parameters to configure
        params = signature(tool_function).parameters
        if not params:
            print(f"✅ Automatically configured `{tool_name}` as it requires no parameters.")
            self._configured_tools.append(tool_config)
            return

        # If there are parameters, ask for static values
        for param_name, param_details in params.items():
            value = input(f"  Please provide a static value for the `{param_name}` parameter (or press Enter to skip): ")
            if value:
                tool_config["parameters"][param_name] = value
        
        self._configured_tools.append(tool_config)
        print(f"✅ Configured `{tool_name}`.")


    def _generate_json_file(self, agent_name: str, description: str, topic_text: str):
        """Saves the final configuration, including the topic text, to a JSON file."""
        config = {
            "agent_name": agent_name,
            "description": description,
            "topic": topic_text, # ✨ FIX: Added the generated topic to the JSON
            "tools": self._configured_tools
        }
        file_name = f"{agent_name.replace(' ', '_').lower()}_config.json"
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            print("-" * 30)
            print(f"✅ Workflow configuration successfully saved to '{file_name}'!")
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