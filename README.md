# simple-agent

一个采用 Pydantic 风格的 AI Agent 实现，支持工具分发、任务管理和团队协作。

[English](./README_EN.md) | 简体中文

## 特性

- **多提供商支持**：支持 Anthropic、OpenAI、Gemini、Groq 和本地模型 (Ollama)
- **工具分发**：可扩展的工具系统，内置 25+ 工具
- **任务管理**：基于文件的持久化任务跟踪
- **团队协作**：多代理系统，支持消息总线
- **上下文压缩**：自动对话压缩
- **Pydantic 模型**：类型安全的配置和数据验证
- **CLI 界面**：基于 Typer 的现代命令行界面

## 项目结构

```
simple-agent/
├── src/simple_agent/
│   ├── agent/          # Agent 核心 (base.py, loop.py)
│   ├── tools/          # 工具系统
│   ├── managers/       # 任务、待办、后台、消息等管理器
│   ├── models/         # Pydantic 模型 (配置、消息、任务)
│   ├── providers/      # AI 提供商实现
│   ├── utils/          # 压缩、安全工具
│   └── cli.py          # CLI 入口
├── tests/              # 测试文件
└── pyproject.toml      # 项目配置
```

## 安装

### 前置要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)（推荐的包管理器）

### 使用 uv 安装

```bash
# 克隆仓库
cd simple-agent

# 使用 uv 安装依赖
uv sync

# 或全局安装
uv pip install -e .
```

## 配置

在项目根目录创建 `.env` 文件：

```env
# Anthropic API
ANTHROPIC_BASE_URL=https://api.anthropic.com
MODEL_ID=claude-sonnet-4-20250514

# 可选设置
TOKEN_THRESHOLD=100000
MAX_TOKENS=8000
POLL_INTERVAL=5
IDLE_TIMEOUT=60
BASH_TIMEOUT=120
```

## AI 提供商

simple-agent 原生支持多个 AI 提供商：

### 可用提供商

| 提供商 | 描述 | 模型 |
|--------|------|------|
| `anthropic` | Anthropic Claude（默认） | claude-sonnet-4, claude-3-5-sonnet, claude-3-5-haiku |
| `openai` | OpenAI GPT 模型 | gpt-4o, o1, o3-mini, gpt-4o-mini |
| `gemini` | Google Gemini | gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash |
| `groq` | Groq 快速推理 | llama-3.3-70b, mixtral-8x7b, gemma2-9b |
| `local` | 本地模型 (Ollama) | llama3.2, qwen2.5, mistral, codellama |

### 提供商配置

在 `.env` 文件中设置相应的 API 密钥：

```env
# Anthropic（默认）
ANTHROPIC_API_KEY=你的密钥

# OpenAI
OPENAI_API_KEY=你的密钥

# Google Gemini
GEMINI_API_KEY=你的密钥

# Groq
GROQ_API_KEY=你的密钥

# 本地模型 (Ollama) - 无需 API 密钥
# 确保运行中：ollama serve
```

### 使用 Ollama 本地模型

要使用本地模型，你需要安装并运行 Ollama：

```bash
# 安装 Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# 或从 https://ollama.com 下载 Windows 版本

# 拉取模型
ollama pull llama3.2

# 启动 Ollama 服务
ollama serve

# 使用 simple-agent
uv run simple-agent --provider local chat
uv run simple-agent --provider local --model codellama run "编写一个 Python 函数"
```

### 使用不同的提供商

```bash
# 使用 OpenAI
uv run simple-agent --provider openai chat

# 使用 Gemini
uv run simple-agent --provider gemini run "解释量子计算"

# 使用 Groq 快速推理
uv run simple-agent --provider groq chat

# 使用本地模型（需要 Ollama 运行中）
uv run simple-agent --provider local chat
```

### 列出可用提供商

```bash
uv run simple-agent providers
```

## 使用方法

### CLI 命令

```bash
# 显示帮助
uv run simple-agent --help
# 或
python -m simple_agent.cli --help

# 交互式聊天模式
uv run simple-agent chat

# 单次提示执行
uv run simple-agent run "列出当前目录的所有文件"

# 任务管理
uv run simple-agent task-list
uv run simple-agent task-create "修复认证模块的 bug" --description "JWT token 过期太快"
uv run simple-agent task-get 1

# 团队管理
uv run simple-agent team-list

# 查看收件箱
uv run simple-agent inbox

# 显示版本
uv run simple-agent version
```

### 可用命令

| 命令 | 描述 |
|------|------|
| `chat` | 启动交互式聊天模式 |
| `run` | 运行单次提示并退出 |
| `providers` | 列出可用的 AI 提供商 |
| `task-list` | 列出所有任务 |
| `task-create` | 创建新任务 |
| `task-get` | 按 ID 获取任务详情 |
| `team-list` | 列出所有队友 |
| `inbox` | 显示队长的收件箱 |
| `compact` | 管理对话压缩 |
| `version` | 显示版本信息 |

### 选项

| 选项 | 简写 | 描述 |
|------|------|------|
| `--provider` | `-p` | AI 提供商 (anthropic, openai, gemini, groq, local) |
| `--model` | `-m` | 覆盖模型 ID |
| `--workdir` | `-w` | 覆盖工作目录 |

### 开发

```bash
# 安装开发依赖
uv sync --all-extras

# 使用 ruff 格式化代码
uv run ruff format src/

# 检查代码
uv run ruff check src/

# 运行测试
uv run pytest
```

## 架构

### Pydantic 模型

所有数据结构都使用 Pydantic 进行验证：

```python
from simple_agent.models import Settings, TodoItem, Task

settings = Settings()
todo = TodoItem(content="任务", status="pending", activeForm="工作中")
```

### 工具系统

工具通过集中处理器注册和分发：

```python
from simple_agent.tools import TOOL_HANDLERS

# 执行工具
result = TOOL_HANDLERS["bash"](command="ls -la")
```

### Agent 核心

```python
from simple_agent.agent import Agent

agent = Agent()
response = agent.process_query("这个目录里有什么文件？")
```

## 从 main.py 迁移

原始的 `main.py` 已重构为模块化组件：

| 原始位置 | 新位置 |
|----------|--------|
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

## 许可证

MIT
