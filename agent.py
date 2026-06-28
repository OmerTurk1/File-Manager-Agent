from openai import OpenAI
from pydantic import BaseModel, Field, model_validator
from typing import Any, Union

AllowedParamTypes = Union[str, int, float, bool, list[str], dict[str, str]]

class OutputFormat(BaseModel):
    finished: bool = Field(
        ...,
        description="Whether the task is complete. Set to True only if you are providing the final_answer."
    )
    tool_name: str | None = Field(
        None,
        description="Tool name to call. MUST be provided if finished is False."
    )
    input_parameters: list[AllowedParamTypes] = Field(
        default_factory=list,
        description="Arguments for the tool. MUST be empty if finished is True."
    )
    final_answer: str | None = Field(
        None,
        description="Answer to return if finished=True. MUST be provided if finished is True."
    )

    @model_validator(mode='after')
    def validate_logic(self):
        if self.finished:
            if not self.final_answer:
                raise ValueError("If finished is True, final_answer must be provided.")
            if self.tool_name:
                raise ValueError("If finished is True, tool_name must be None.")
        
        else:
            if not self.tool_name:
                raise ValueError("If finished is False, you MUST specify a tool_name to call. Do not leave it None.")
            if self.final_answer:
                raise ValueError("If finished is False, final_answer must be None.")
                
        return self

class Agent:
    def __init__(self, apikey):
        self.old_memory = []
        self.current_run_steps = []
        self.client = OpenAI(api_key=apikey)

    def start_new_task(self, user_input: str):
        self.current_run_steps = [
            {"role": "user", "content": user_input}
        ]

    def add_tool_execution(self, tool_name: str, inputs: list, output: Any):
        self.current_run_steps.append({
            "role": "assistant",
            "content": f"Called tool '{tool_name}' with parameters {inputs}."
        })
        self.current_run_steps.append({
            "role": "user",
            "content": f"Tool '{tool_name}' returned: {str(output)}"
        })

    def finish_task(self, final_answer: str):
        """Görev tamamlandığında mevcut akışı kalıcı hafızaya taşır ve temizler."""
        if self.current_run_steps:
            task_summary = f"User: {self.current_run_steps[0]['content']} | Answer: {final_answer}"
            self.old_memory.append(task_summary)
        
        self.current_run_steps = []

    def send_to_model(self, tools_schema: list, ai_model : str):
        memory_context = "\n".join([f"- {m}" for m in self.old_memory]) if self.old_memory else "None"
        
        system_instruction = {
            "role": "system",
            "content": f"""You are a database manager agent.

Available tools:
{tools_schema}

Historical context from past sessions:
{memory_context}

CRITICAL RULES FOR OUTPUT FORMAT:
1. You have ONLY two valid states:
   - STATE A (Call a Tool): Set finished=False, tool_name='ToolName', and provide input_parameters. final_answer MUST be null.
   - STATE B (Finish Task): Set finished=True, final_answer='Your detailed response', tool_name=null, and input_parameters=[].
2. NEVER output finished=False with tool_name=null. If you have nothing else to run, you MUST finish the task and provide a final answer.

Return a valid OutputFormat object complying strictly with these two states."""
        }

        messages = [system_instruction] + self.current_run_steps

        raw_completion = self.client.beta.chat.completions.parse(
            model=ai_model, 
            messages=messages,
            response_format=OutputFormat
        )

        parsed_object = raw_completion.choices[0].message.parsed
        usage_info = raw_completion.usage 

        return parsed_object, usage_info