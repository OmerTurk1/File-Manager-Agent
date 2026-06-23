import inspect
import tools
import agent
import traceback
import os
from dotenv import load_dotenv

load_dotenv()

TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object"
}

FRONT_CHARS = int(os.getenv("FRONT_CHARS"))
BACK_CHARS = int(os.getenv("BACK_CHARS"))
def truncate_strings(data):
    if isinstance(data, dict):
        return {k: truncate_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [truncate_strings(item) for item in data]
    elif isinstance(data, str):
        if len(data) > (FRONT_CHARS + BACK_CHARS + 3):
            return f"{data[:FRONT_CHARS]}...{data[-BACK_CHARS:]}"
        return data
    return data

def build_tools():
    tool_schemas = []
    for name, func in inspect.getmembers(tools, inspect.isfunction):
        if not getattr(func, "is_tool", False):
            continue
        
        signature = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in signature.parameters.items():
            annotation = param.annotation
            json_type = TYPE_MAP.get(annotation, "string")
            properties[param_name] = {"type": json_type}
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        tool_schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": inspect.getdoc(func) or "",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        })
    return tool_schemas

def main():
    tool_schemas = build_tools()
    agent_instance = agent.Agent()

    print("--- Database Manager Agent Started ---")

    while True:
        user_input = input("\n >>> Make your query (or 'exit'):").strip()

        if user_input.lower() == 'exit':
            break
        if user_input == "":
            print("Write something meaningful!")
            continue

        agent_instance.start_new_task(user_input)
        
        work_finished = False
        response = None

        total_prompt_tokens = 0
        total_completion_tokens = 0

        while not work_finished:
            response, usage = agent_instance.send_to_model(tools_schema=tool_schemas)

            if usage:
                total_prompt_tokens += usage.prompt_tokens
                total_completion_tokens += usage.completion_tokens

            if response.finished:
                work_finished = True
                agent_instance.finish_task(response.final_answer)
                print(f" <<< {response.final_answer}")
            else:
                if not response.tool_name:
                    print("Status: Agent got stuck without calling a tool.")
                    break

                try:
                    selected_tool = getattr(tools, response.tool_name)
                    inputs = response.input_parameters

                    truncated_inputs = truncate_strings(inputs)
                    print(f" - TOOL CALL: {response.tool_name} | INPUTS: {truncated_inputs}")

                    if isinstance(inputs, dict):
                        tool_output = selected_tool(**inputs)
                    elif isinstance(inputs, list):
                        tool_output = selected_tool(*inputs)
                    else:
                        tool_output = selected_tool(inputs)

                    agent_instance.add_tool_execution(response.tool_name, inputs, tool_output)

                except AttributeError:
                    error_msg = f"Error: Tool '{response.tool_name}' does not exist."
                    print(f" - {error_msg}")
                    agent_instance.add_tool_execution(response.tool_name, inputs, error_msg)
                except Exception as e:
                    error_msg = f"Error executing tool: {str(e)}"
                    print(f" - {error_msg}")
                    traceback.print_exc()
                    agent_instance.add_tool_execution(response.tool_name, inputs, error_msg)

        print(f" [Token Usage -> Prompt: {total_prompt_tokens} | Completion: {total_completion_tokens} | Total: {total_prompt_tokens + total_completion_tokens}]")

    print("Agent Goes Back To Sleep")

if __name__ == "__main__":
    main()