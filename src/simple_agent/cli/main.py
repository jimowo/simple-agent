"""CLI interface for simple-agent."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from simple_agent.agent.base import Agent
from simple_agent.agent.loop import agent_loop
from simple_agent.cli import InteractivePrompt
from simple_agent.models.config import Settings, create_settings
from simple_agent.permissions.manager import PermissionManager

app = typer.Typer(
    name="simple-agent",
    help="A Pydantic-style AI Agent with tool dispatch, task management, and team collaboration.",
    add_completion=False,
)
console = Console()


class ConsoleStatusController:
    """Status controller that manages Rich console.status during permission requests.

    This allows the permission manager to pause/resume the status spinner
    when user interaction is needed.
    """

    def __init__(self, console_instance: Console):
        """Initialize the status controller.

        Args:
            console_instance: Rich Console instance
        """
        self._console = console_instance
        self._status_context = None

    def set_status_context(self, status_context):
        """Set the active status context.

        Args:
            status_context: The console.status context manager
        """
        self._status_context = status_context

    def pause(self) -> None:
        """Pause the status display by hiding the status."""
        if self._status_context is not None:
            # Rich doesn't have a direct pause method, so we use console.line()
            # to add visual separation
            self._console.line(count=2)

    def resume(self) -> None:
        """Resume the status display (no-op for Rich status)."""
        # Rich status automatically resumes, no action needed
        pass


def _get_agent(settings: Settings = None, permission_manager: PermissionManager = None) -> Agent:
    """Get agent instance with optional settings and permission manager.

    Args:
        settings: Optional settings instance
        permission_manager: Optional pre-configured permission manager

    Returns:
        Agent instance
    """
    return Agent(settings or Settings(), permission_manager=permission_manager)


@app.callback()
def main(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override model ID"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider (anthropic, openai, gemini, groq, local)"),
    workdir: Optional[str] = typer.Option(
        None, "--workdir", "-w", help="Override working directory"
    ),
):
    """Global options for simple-agent."""
    settings_dict = {}
    if model:
        settings_dict["model_id"] = model
    if provider:
        settings_dict["provider"] = provider
    if workdir:
        settings_dict["workdir"] = Path(workdir)

    ctx.obj = create_settings(**settings_dict) if settings_dict else None


@app.command("chat")
def chat_command(
    ctx: typer.Context,
):
    """Start interactive chat mode."""
    settings = ctx.obj or Settings()

    # Create permission manager with status controller
    status_controller = ConsoleStatusController(console)
    permission_manager = PermissionManager(status_controller=status_controller)

    agent = _get_agent(settings, permission_manager)
    history = []

    provider_name = settings.get_active_provider()
    console.print(f"[cyan]simple-agent[/cyan] - AI Agent at {settings.workdir}")
    console.print(f"Provider: [green]{provider_name}[/green] | Model: [yellow]{settings.model_id or 'default'}[/yellow]")
    console.print("Type 'exit' or 'quit' to end the session.")
    console.print("Use [cyan]↑/↓[/cyan] arrows for history, [cyan]Tab[/cyan] for completion.\n")

    # Create interactive prompt with history support
    prompt_session = InteractivePrompt(
        history_file=settings.workdir / ".chat_history",
        history_size=1000,
        enable_completion=True,
    )

    while True:
        try:
            query = prompt_session.prompt("\n>>> ")
        except (EOFError, KeyboardInterrupt):
            break

        if query.strip().lower() in ("q", "exit", "quit", ""):
            console.print("[yellow]Goodbye![/yellow]")
            break

        history.append({"role": "user", "content": query})

        # Use status with explicit end to allow permission panels to display properly
        status = console.status("[bold green]Thinking...", spinner="dots")
        status.start()
        try:
            agent_loop(history, agent)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            status.stop()
            continue
        status.stop()

        # Display response
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    response = ""
                    for c in content:
                        if hasattr(c, "text"):
                            response = c.text
                            break
                    if response:
                        console.print(Markdown(response))
                break

        console.print()


@app.command("run")
def run_command(
    ctx: typer.Context,
    prompt: str = typer.Argument(..., help="Prompt to execute"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """Run a single prompt and exit."""
    settings = ctx.obj or Settings()

    # Create permission manager with status controller
    status_controller = ConsoleStatusController(console)
    permission_manager = PermissionManager(status_controller=status_controller)

    agent = _get_agent(settings, permission_manager)

    if verbose:
        console.print(f"[cyan]Executing:[/cyan] {prompt}\n")

    history = [{"role": "user", "content": prompt}]

    # Use status with explicit control
    status = console.status("[bold green]Processing...", spinner="dots")
    status.start()
    try:
        agent_loop(history, agent)
    except Exception as e:
        status.stop()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    status.stop()

    # Display response
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                response = ""
                for c in content:
                    if hasattr(c, "text"):
                        response = c.text
                        break
                if response:
                    console.print(Markdown(response))
            break


@app.command("task-list")
def task_list_command(ctx: typer.Context):
    """List all tasks."""
    settings = ctx.obj or Settings()
    agent = _get_agent(settings)
    output = agent.task_mgr.list_all()
    console.print(output)


@app.command("task-create")
def task_create_command(
    ctx: typer.Context,
    subject: str = typer.Argument(..., help="Task subject"),
    description: str = typer.Option("", "--description", "-d", help="Task description"),
):
    """Create a new task."""
    settings = ctx.obj or Settings()
    agent = _get_agent(settings)
    import json

    result = json.loads(agent.task_mgr.create(subject, description))
    console.print(f"[green]Created task #{result['id']}:[/green] {result['subject']}")


@app.command("task-get")
def task_get_command(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="Task ID"),
):
    """Get task details."""
    settings = ctx.obj or Settings()
    agent = _get_agent(settings)
    import json

    result = json.loads(agent.task_mgr.get(task_id))
    console.print(json.dumps(result, indent=2))


@app.command("team-list")
def team_list_command(ctx: typer.Context):
    """List all teammates."""
    settings = ctx.obj or Settings()
    agent = _get_agent(settings)
    output = agent.teammate.list_all()
    console.print(output)


@app.command("inbox")
def inbox_command(ctx: typer.Context):
    """Show lead's inbox."""
    settings = ctx.obj or Settings()
    agent = _get_agent(settings)
    import json

    msgs = agent.bus.read_inbox("lead")
    if msgs:
        console.print(json.dumps(msgs, indent=2))
    else:
        console.print("[yellow]No messages in inbox.[/yellow]")


@app.command("compact")
def compact_command(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Force manual compact"),
):
    """Manage conversation compression."""
    if force:
        console.print("[yellow]Manual compact not implemented in CLI mode[/yellow]")
        console.print("[yellow]Use 'chat' mode for automatic compression[/yellow]")


@app.command("version")
def version_command():
    """Show version information."""
    from simple_agent import __version__

    console.print(f"simple-agent version [cyan]{__version__}[/cyan]")


@app.command("providers")
def providers_command():
    """List available AI providers."""
    from simple_agent.providers import ProviderFactory

    providers = ProviderFactory.list_providers()

    console.print("\n[bold]Available AI Providers:[/bold]\n")
    for provider in sorted(providers):
        console.print(f"  - [cyan]{provider}[/cyan]")

    console.print("\n[bold]Usage:[/bold]")
    console.print("  simple-agent --provider <provider> chat")
    console.print("  simple-agent --provider openai run \"Hello\"\n")

    console.print("[bold]Environment Variables:[/bold]")
    console.print("  ANTHROPIC_API_KEY  - For Anthropic Claude")
    console.print("  OPENAI_API_KEY     - For OpenAI GPT models")
    console.print("  GEMINI_API_KEY     - For Google Gemini")
    console.print("  GROQ_API_KEY       - For Groq fast inference")
    console.print("  (local provider uses Ollama at http://localhost:11434)\n")


def main_cli():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main_cli()
