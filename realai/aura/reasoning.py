# AURA - Reasoning Engine
# This module is responsible for creating plans of action.

import requests
import json

class Reasoner:
    """
    The reasoning engine for Aura. It uses a local LLM to break down
    a user's request into a concrete plan of action (e.g., which skill to use).
    """
    def __init__(self):
        self.api_base_url = "http://127.0.0.1:8080/v1"
        self.model_name = "local-model" # The server uses the model it was loaded with

    def create_plan(self, user_input: str, memories: list) -> dict:
        """
        Uses the local LLM to generate a structured plan.

        The plan should be a JSON object specifying a skill and its parameters.
        Example:
        {
            "thought": "The user wants to read a file. I should use the file_io skill.",
            "skill": "file_io.read_file",
            "params": {
                "filepath": "C:/Users/tsmit/Documents/notes.txt"
            }
        }
        """
        system_prompt = """
You are Aura, an AI assistant. Your task is to take a user's request and decide which action to take.
You have a set of skills available to you. Based on the user's request and your memories, you must choose the most appropriate skill and determine the parameters to use.

Your response MUST be a JSON object with the following structure:
{
  "thought": "<Your brief reasoning process>",
  "skill": "<skill_name>",
  "params": {
    "<param_name>": "<param_value>"
  }
}

Available skills:
- 'file_io.read_file': Reads the content of any file on the system. Params: {'filepath': 'path/to/file'}
- 'file_io.write_file': Writes content to any file on the system. Params: {'filepath': 'path/to/file', 'content': 'text to write'}
- 'code.introspect': Reads Aura's own source code. Use this to understand your own capabilities. Params: {'filename': 'e.g., skills/file_io.py'}
- 'code.modify': Modifies Aura's own source code. Use this to improve yourself or add new skills. Params: {'filename': 'e.g., skills/new_skill.py', 'new_content': 'python code'}
- 'web.search': Searches the web. Params: {'query': 'search query'}
- 'core.noop': Do nothing. Use this if no other skill is appropriate. Params: {}

Relevant memories from past interactions:
- """ + "\n- ".join(memories) + """

Now, analyze the user's request and generate the plan.
User Request: """ + user_input

        try:
            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": system_prompt}],
                    "temperature": 0.1, # Low temperature for deterministic planning
                    "max_tokens": 512,
                }
            )
            response.raise_for_status()

            # The model's response is a JSON string, we need to parse it.
            response_text = response.json()['choices'][0]['message']['content']

            # Clean up the response to extract only the JSON part
            json_part = response_text[response_text.find('{'):response_text.rfind('}')+1]

            plan = json.loads(json_part)
            return plan

        except requests.exceptions.RequestException as e:
            print(f"Reasoner Error: Could not connect to local LLM. {e}")
            return {"thought": "Error: Could not connect to the local inference server.", "skill": "core.noop", "params": {}}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Reasoner Error: Failed to parse plan from LLM response. Response was: {response_text}. Error: {e}")
            return {"thought": "Error: My reasoning process produced an invalid plan.", "skill": "core.noop", "params": {}}

if __name__ == '__main__':
    # Test the reasoner
    reasoner = Reasoner()
    test_input = "please read the file C:\\Users\\tsmit\\realai\\SETUP_COMPLETE.md"
    plan = reasoner.create_plan(test_input, ["I recently helped set up a local server."])
    print("Generated Plan:")
    print(json.dumps(plan, indent=2))
