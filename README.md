# simple-agent

A Pydantic-style AI Agent implementation with tool dispatch, task management, and team collaboration.

## Features

- **Tool Dispatch**: Extensible tool system with 25+ built-in tools
- **Task Management**: Persistent file-based task tracking
- **Team Collaboration**: Multi-agent system with message bus
- **Context Compression**: Automatic conversation compression
- **Pydantic Models**: Type-safe configuration and data validation
- **CLI Interface**: Modern Typer-based command-line interface

## Project Structure

```
simple-agent/
├── src/simple_agent/
│   ├── agent/          # Agent core (base.py, loop.py)
│   ├── tools/          # Tool system
│   ├── managers/       # Task, todo, background, messaging, etc.
│   ├── models/         # Pydantic models (config, messages, tasks)
│   ├── utils/          # Compression, safety utilities
│   └── cli.py          # CLI entry point
├── tests/              # Test files
└── pyproject.toml      # Project configuration
```

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended package manager)

### Setup with uv

```bash
# Clone the repository
cd simple-agent

# Install dependencies with uv
uv sync

# Or install globally
uv pip install -e .
```

## Configuration

Create a `.env` file in the project root:

```env
# Anthropic API
ANTHROPIC_BASE_URL=https://api.anthropic.com
MODEL_ID=claude-sonnet-4-20250514

# Optional settings
TOKEN_THRESHOLD=100000
MAX_TOKENS=8000
POLL_INTERVAL=5
IDLE_TIMEOUT=60
BASH_TIMEOUT=120
```

## Usage

### CLI Commands

```bash
# Show help
uv run simple-agent --help
# or
python -m simple_agent.cli --help

# Interactive chat mode
uv run simple-agent chat

# Single prompt execution
uv run simple-agent run "List all files in the current directory"

# Task management
uv run simple-agent task-list
uv run simple-agent task-create "Fix bug in auth module" --description "JWT token expires too soon"
uv run simple-agent task-get 1

# Team management
uv run simple-agent team-list

# View inbox
uv run simple-agent inbox

# Show version
uv run simple-agent version
```

### Available Commands

| Command | Description |
|---------|-------------|
| `chat` | Start interactive chat mode |
| `run` | Run a single prompt and exit |
| `task-list` | List all tasks |
| `task-create` | Create a new task |
| `task-get` | Get task details by ID |
| `team-list` | List all teammates |
| `inbox` | Show lead's inbox |
| `compact` | Manage conversation compression |
| `version` | Show version information |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | Override model ID |
| `--workdir` | `-w` | Override working directory |

### Development

```bash
# Run with development dependencies
uv sync --all-extras

# Format code with ruff
uv run ruff format src/

# Lint code
uv run ruff check src/

# Run tests
uv run pytest
```

## Architecture

### Pydantic Models

All data structures use Pydantic for validation:

```python
from simple_agent.models import Settings, TodoItem, Task

settings = Settings()
todo = TodoItem(content="Task", status="pending", activeForm="Working")
```

### Tool System

Tools are registered and dispatched through a centralized handler:

```python
from simple_agent.tools import TOOL_HANDLERS

# Execute a tool
result = TOOL_HANDLERS["bash"](command="ls -la")
```

### Agent Core

```python
from simple_agent.agent import Agent

agent = Agent()
response = agent.process_query("What files are in this directory?")
```

## Migration from main.py

The original `main.py` has been refactored into modular components:

| Original | New Location |
|----------|--------------|
| `run_bash()` | `tools/bash_tools.py` |
| `run_read()` | `tools/file_tools.py` |
| `TodoManager` | `managers/todo.py` |
| `TaskManager` | `managers/task.py` |
| `BackgroundManager` | `managers/background.py` |
| `MessageBus` | `managers/message.py` |
| `TeammateManager` | `managers/teammate.py` |
| `SkillLoader` | `managers/skill.py` |
| `agent_loop()` | `agent/loop.py` |
| REPL | `cli.py` (Typer) |

## License

MIT
