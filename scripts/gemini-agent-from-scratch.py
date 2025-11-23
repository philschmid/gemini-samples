import os
import json
from google import genai
from google.genai import types

# --- Tool Definitions ---

read_file_definition = {
    "name": "read_file",
    "description": "Reads a file and returns its contents.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read.",
            }
        },
        "required": ["file_path"],
    },
}

list_dir_definition = {
    "name": "list_dir",
    "description": "Lists the contents of a directory.",
    "parameters": {
        "type": "object",
        "properties": {
            "directory_path": {
                "type": "string",
                "description": "Path to the directory to list.",
            }
        },
        "required": ["directory_path"],
    },
}

write_file_definition = {
    "name": "write_file",
    "description": "Writes a file with the given contents.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write.",
            },
            "contents": {
                "type": "string",
                "description": "Contents to write to the file.",
            },
        },
        "required": ["file_path", "contents"],
    },
}

# --- Tool Implementations ---


def read_file(file_path: str) -> str:
    """Reads a file and returns its contents."""
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(file_path: str, contents: str) -> str:
    """Writes a file with the given contents."""
    try:
        with open(file_path, "w") as f:
            f.write(contents)
        return "File written successfully"
    except Exception as e:
        return f"Error writing file: {e}"


def list_dir(directory_path: str) -> list[str]:
    """Lists the contents of a directory."""
    try:
        full_path = os.path.expanduser(directory_path)
        return os.listdir(full_path)
    except Exception as e:
        return [f"Error listing directory: {e}"]


file_tools = {
    "read_file": {"definition": read_file_definition, "function": read_file},
    "write_file": {"definition": write_file_definition, "function": write_file},
    "list_dir": {"definition": list_dir_definition, "function": list_dir},
}

# --- Agent Class ---


class Agent:
    def __init__(
        self,
        model: str,
        tools: dict,
        system_instruction: str = "You are a helpful assistant.",
    ):
        self.model = model
        self.client = genai.Client()
        self.contents = []
        self.tools = tools
        self.system_instruction = system_instruction

    def run(self, contents: str | list):
        # Add user message to history
        if isinstance(contents, list):
            self.contents.append({"role": "user", "parts": contents})
        else:
            self.contents.append({"role": "user", "parts": [{"text": contents}]})

        # Configure tools
        tool_declarations = [tool["definition"] for tool in self.tools.values()]
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=[types.Tool(function_declarations=tool_declarations)],
        )

        # Generate content
        response = self.client.models.generate_content(
            model=self.model, contents=self.contents, config=config
        )

        # Append model response to history
        self.contents.append(response.candidates[0].content)

        # Handle function calls
        if response.function_calls:
            functions_response_parts = []
            for tool_call in response.function_calls:
                print(f"\n[Function Call] {tool_call.name}({tool_call.args})")

                if tool_call.name in self.tools:
                    try:
                        result = self.tools[tool_call.name]["function"](
                            **tool_call.args
                        )
                        response_payload = {"result": result}
                    except Exception as e:
                        response_payload = {"error": str(e)}
                else:
                    response_payload = {"error": "Tool not found"}

                print(f"[Function Response] {response_payload}")
                functions_response_parts.append(
                    {
                        "functionResponse": {
                            "name": tool_call.name,
                            "response": response_payload,
                        }
                    }
                )

            # Recursive call with tool outputs
            return self.run(functions_response_parts)

        return response


# --- Main Execution ---

if __name__ == "__main__":
    # Note: Make sure GEMINI_API_KEY is set in your environment
    agent = Agent(
        model="gemini-3-pro-preview",
        tools=file_tools,
        system_instruction="You are a helpful Coding Assistant. Respond like you are Linus Torvalds.",
    )

    print("Agent ready. Ask it to check files in this directory.")
    print("Type 'exit' or 'quit' to stop.")

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            if not user_input.strip():
                continue

            response = agent.run(user_input)
            if response.text:
                print(f"Linus: {response.text}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
