import inspect
import tools
import agent

TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object"
}

def build_tools():
    tool_schemas = []

    for name, func in inspect.getmembers(tools, inspect.isfunction):
        signature = inspect.signature(func)

        properties = {}
        required = []

        for param_name, param in signature.parameters.items():
            annotation = param.annotation

            json_type = TYPE_MAP.get(annotation, "string")

            properties[param_name] = {
                "type": json_type
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        tool_schemas.append(
            {
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
            }
        )

    return tool_schemas

def main():
    tool_schemas = build_tools()

    agent_instance = agent.Agent()

    running = True
    while running:

        user_input = input(" >>> Make your query:").strip()

        if user_input == "":
            print("Write something meaningful!")
            continue

        # message management: first user role, then tool calls
        message_role = "user"
        new_message = user_input
        while not work_finished:
            response = agent_instance.send_to_model(
                new_message,
                role=message_role,
                tools=tool_schemas
            )

            selected_tool = getattr(tools, response.tool_name)
            inputs = response.input_parameters

            print(f" - TOOL CALL: {selected_tool.name}  INPUTS: {inputs}")

            if isinstance(inputs, dict):
                tool_output = selected_tool(**inputs)
            elif isinstance(inputs, list):
                tool_output = selected_tool(*inputs)
            else:
                tool_output = selected_tool(inputs)
            
            new_message = tool_output
            message_role = "tool_output"
            work_finished = response.finished
            
        print(f" <<< {response.final_answer}")

if __name__=="__main__":
    main()