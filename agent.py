from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Any

client = OpenAI()

class OutputFormat(BaseModel):
    finished: bool = Field(
        ...,
        description="Whether the task is complete"
    )

    tool_name: str | None = Field(
        None,
        description="Tool name to call"
    )

    input_parameters: list[Any] = Field(
        default_factory=list,
        description="Arguments for the tool"
    )

    final_answer: str | None = Field(
        None,
        description="Answer to return if finished=True"
    )

class Agent:
    def __init__(self):
        self.current_user_input = None
        self.tool_outputs = []
        self.old_memory = []

    def add_user_input(self, text):
        self.current_user_input = text
        self.tool_outputs = []

    def add_tool_output(self, output):
        self.tool_outputs.append(str(output))

    def finish_task(self):
        if self.current_user_input is not None:
            self.old_memory.append(self.current_user_input)

        self.current_user_input = None
        self.tool_outputs = []

    def send_to_model(self, message, role, tools):
        
        response = client.beta.chat.completions.parse(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": f"""
    You are a database manager agent.

    Available tools:
    {tools}

    Return a valid OutputFormat object.
    """
                },
                {
                    "role": role,
                    "content": message
                }
            ],
            response_format=OutputFormat
        )

        return response.choices[0].message.parsed