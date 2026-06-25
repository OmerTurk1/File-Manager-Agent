# FileManagerAgent

FileManagerAgent is a Python project designed to manage file system operations and data analysis through an OpenAI-powered agent. The project accepts user input, selects the appropriate tool calls, and processes the results.

## Main components

- `pipeline.py`: Manages the agent loop and builds tool schemas. Reads user input, communicates with OpenAI, executes tool calls, and handles responses.
- `agent.py`: Stores conversation history, task initialization, tool outputs, and completed tasks. Generates system instructions sent to the OpenAI model.
- `tools.py`: Includes tools for creating, deleting, moving, reading files/folders, searching directories, executing SQL queries, summarizing datasets, and querying tables. It enforces path safety and two root directory boundaries.
- `.env.example`: Example configuration for working directories, view-only folder root, truncation settings, and the OpenAI API key.

## Features

- Root folder restrictions: Prevents unauthorized access with `MAIN_ROOT_FOLDER` and `VIEWABLE_FOLDER_ROOT`.
- Tool-based architecture: Each `@register_tool` function in `tools.py` becomes callable by the agent.
- SQL and data analysis support: Executes SQLite queries and provides summaries and filtering for CSV/Excel/Parquet files.
- Message-based state management: The agent logs tool calls and responses for each task.

## Run

1. Create a `.env` file and populate required values using `.env.example`.
2. Install dependencies with `pip install -r requirements.txt`.
3. Start the web UI from the project root with `python app.py`.
4. Open `http://127.0.0.1:5000` in your browser.

## Important notes

- `OPENAI_API_KEY` must be set.
- `MAIN_ROOT_FOLDER` requires write permissions; `VIEWABLE_FOLDER_ROOT` can be configured for view-only access.
- `tools.py` validates paths to prevent access outside allowed roots.
- `pipeline.py` handles OpenAI output as either tool calls or final results and reports token usage when tasks complete.

## Use cases

- Create new files or folders inside the project workspace.
- Read, clear, or delete existing files.
- Generate summary statistics from data files.
- Run queries on a SQLite database.
- Filter and preview data from CSV/Excel/Parquet files.
