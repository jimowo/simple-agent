# simple-agent

A Pydantic-style AI Agent implementation with tool dispatch, task management, and team collaboration.

English | [简体中文](./README.md)

## Features

- **Multi-Provider Support**: Support for Anthropic, OpenAI, Gemini, Groq, and local models (Ollama)
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
│   ├── providers/      # AI provider implementations
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

## AI Providers

simple-agent supports multiple AI providers out of the box:

### Available Providers

| Provider | Description | Models |
|----------|-------------|--------|
| `anthropic` | Anthropic Claude (default) | claude-sonnet-4, claude-3-5-sonnet, claude-3-5-haiku |
| `openai` | OpenAI GPT models | gpt-4o, o1, o3-mini, gpt-4o-mini |
| `gemini` | Google Gemini | gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash |
| `groq` | Groq fast inference | llama-3.3-70b, mixtral-8x7b, gemma2-9b |
| `local` | Local models via Ollama | llama3.2, qwen2.5, mistral, codellama |

### Provider Configuration

Set the appropriate API key in your `.env` file:

```env
# Anthropic (default)
ANTHROPIC_API_KEY=your_key_here

# OpenAI
OPENAI_API_KEY=your_key_here

# Google Gemini
GEMINI_API_KEY=your_key_here

# Groq
GROQ_API_KEY=your_key_here

# Local models (Ollama) - no API key needed
# Make sure Ollama is running: ollama serve
```

### Local Models with Ollama

To use local models, you need to install and run Ollama:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Or download from https://ollama.com for Windows

# Pull a model
ollama pull llama3.2

# Start the Ollama server
ollama serve

# Use with simple-agent
uv run simple-agent --provider local chat
uv run simple-agent --provider local --model codellama run "Write a Python function"
```

### Using Different Providers

```bash
# Use OpenAI
uv run simple-agent --provider openai chat

# Use Gemini
uv run simple-agent --provider gemini run "Explain quantum computing"

# Use Groq for fast inference
uv run simple-agent --provider groq chat

# Use local models (Ollama must be running)
uv run simple-agent --provider local chat
```

### List Available Providers

```bash
uv run simple-agent providers
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
| `providers` | List available AI providers |
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
| `--provider` | `-p` | AI provider (anthropic, openai, gemini, groq, local) |
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

Tools are executed through `ToolHandlerRegistry`:

```python
from simple_agent.agent.context import AgentContext
from simple_agent.tools import ToolHandlerRegistry

context = AgentContext.from_container(settings)
registry = ToolHandlerRegistry(context)
result = registry.handle_bash("echo hello")
```

### Agent Core

```python
from simple_agent.agent import Agent

agent = Agent()
response = agent.process_query("What files are in this directory?")
```

For new code, prefer the modern initialization path:

```python
from simple_agent.agent import Agent
from simple_agent.agent.context import AgentContext

agent = Agent()

# Or inject a pre-built context when you need shared managers.
context = AgentContext.from_container(settings)
agent = Agent(context=context)
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
| `AgentLoop` | `agent/loop.py` |
| REPL | `cli.py` (Typer) |

## License

MIT
