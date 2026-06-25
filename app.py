# libraries
from flask import Flask, render_template, jsonify, request, Response
import json
import os
import inspect
import traceback
import webbrowser

# my files
import agent
import tools

PREFERENCES_FILE = "preferences.json"

app = Flask(__name__)
preferences = {}
TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object"
}
tool_schemas = None
agent_instance = None

def get_preferences():
    if not os.path.exists(PREFERENCES_FILE):
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "MAIN_ROOT_FOLDER" : "workspace",
                "VIEWABLE_FOLDER_ROOT" : "C:/",
                "FRONT_CHARS" : 12,
                "BACK_CHARS" : 10,
                "OPENAI_API_KEY" : None
            }, f, indent=4)
            
    with open(PREFERENCES_FILE, "r", encoding='utf-8') as f:
        return json.load(f)

def set_preferences(new_prefs):
    with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_prefs, f, indent=4, ensure_ascii=False)

def truncate_strings(data, split_coef=1):
    if isinstance(data, dict):
        return {k: truncate_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [truncate_strings(item) for item in data]
    elif isinstance(data, str):
        front = preferences.get("FRONT_CHARS") * split_coef
        back = preferences.get("BACK_CHARS") * split_coef
        if len(data) > (front + back + 3):
            return f"{data[:front]}...{data[-back:]}"
        return data
    return data

def build_tools():
    schemas = []
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

        schemas.append({
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
    return schemas

@app.route('/')
def index():
    global preferences, tool_schemas, agent_instance
    preferences = get_preferences()
    tool_schemas = build_tools()
    agent_instance = agent.Agent(preferences.get("OPENAI_API_KEY"))
    
    return render_template('index.html', preferences=preferences)

@app.route('/chat_stream')
def chat_stream():
    user_input = request.args.get("user_input", "").strip()

    if not user_input:
        return jsonify({"status": "error", "message": "Input cannot be empty"}), 400

    def generate():
        global preferences, tool_schemas, agent_instance
        
        if not agent_instance:
            preferences = get_preferences()
            tool_schemas = build_tools()
            agent_instance = agent.Agent(preferences.get("OPENAI_API_KEY"))

        try:
            agent_instance.start_new_task(user_input)
        except Exception as task_err:
            yield f"data: {json.dumps({'event': 'error', 'message': f'Task başlatılamadı: {str(task_err)}'})}\n\n".encode('utf-8')
            return

        work_finished = False
        total_prompt_tokens = 0
        total_completion_tokens = 0

        while not work_finished:
            # 🛑 CRITICAL: Model çağrısını korumaya alıyoruz
            try:
                response, usage = agent_instance.send_to_model(tools_schema=tool_schemas)
            except Exception as model_err:
                print("!!! MODEL SORGUSU SIRASINDA HATA OLUŞTU !!!")
                traceback.print_exc() # Konsolunda hatanın satır satır nedenini göreceksin
                yield f"data: {json.dumps({'event': 'error', 'message': f'Model Hatası: {str(model_err)}'}, ensure_ascii=False)}\n\n".encode('utf-8')
                break

            if usage:
                total_prompt_tokens += usage.prompt_tokens
                total_completion_tokens += usage.completion_tokens

            if response.finished:
                work_finished = True
                agent_instance.finish_task(response.final_answer)
                
                final_data = {
                    "event": "final_answer",
                    "message": response.final_answer,
                    "usage": {
                        "total_prompt_tokens": total_prompt_tokens,
                        "total_completion_tokens": total_completion_tokens,
                        "total_token_consumption": total_prompt_tokens + total_completion_tokens
                    }
                }
                yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n".encode('utf-8')
            else:
                if not response.tool_name:
                    yield f"data: {json.dumps({'event': 'error', 'message': 'Agent got stuck without calling a tool.'})}\n\n".encode('utf-8')
                    break

                tool_name = response.tool_name
                inputs = response.input_parameters
                truncated_inputs = truncate_strings(inputs)

                yield f"data: {json.dumps({'event': 'tool_call', 'tool_name': tool_name, 'inputs': truncated_inputs}, ensure_ascii=False)}\n\n".encode('utf-8')

                try:
                    selected_tool = getattr(tools, tool_name)
                    if isinstance(inputs, dict):
                        tool_output = selected_tool(**inputs)
                    elif isinstance(inputs, list):
                        tool_output = selected_tool(*inputs)
                    else:
                        tool_output = selected_tool(inputs)

                    agent_instance.add_tool_execution(tool_name, inputs, tool_output)
                    truncated_outputs = truncate_strings(str(tool_output), split_coef=3)

                    yield f"data: {json.dumps({'event': 'tool_result', 'tool_name': tool_name, 'output': truncated_outputs}, ensure_ascii=False)}\n\n".encode('utf-8')

                except AttributeError:
                    error_msg = f"Error: Tool '{tool_name}' does not exist."
                    agent_instance.add_tool_execution(tool_name, inputs, error_msg)
                    yield f"data: {json.dumps({'event': 'tool_error', 'message': error_msg})}\n\n".encode('utf-8')
                except Exception as e:
                    error_msg = f"Error executing tool: {str(e)}"
                    agent_instance.add_tool_execution(tool_name, inputs, error_msg)
                    yield f"data: {json.dumps({'event': 'tool_error', 'message': error_msg})}\n\n".encode('utf-8')

    # direct_passthrough=True ekleyerek buffer tıkanmalarını önlüyoruz
    return Response(generate(), mimetype='text/event-stream', direct_passthrough=True)

@app.route("/adjust_preferences", methods=["POST"])
def adjust_preferences_route():
    data = request.get_json() or {}
    global preferences
    set_preferences(data)
    preferences = get_preferences() # Bellekteki ayarları güncelle
    return jsonify({"status": "success", "message": "Preferences updated successfully"})

def open_browser():
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open("http://127.0.0.1:5000/")

if __name__ == "__main__":
    open_browser()
    app.run(debug=False, port=5000)