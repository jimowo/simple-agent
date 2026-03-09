"""CLI interface for simple-agent."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from simple_agent.agent.base import Agent
from simple_agent.agent.loop import agent_loop
from simple_agent.models.config import Settings, create_settings

app = typer.Typer(
    name="simple-agent",
    help="A Pydantic-style AI Agent with tool dispatch, task management, and team collaboration.",
    add_completion=False,
)
console = Console()


def _get_agent(settings: Settings = None) -> Agent:
    """Get agent instance with optional settings."""
    return Agent(settings or Settings())


@app.callback()
def main(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override model ID"),
    workdir: Optional[str] = typer.Option(
        None, "--workdir", "-w", help="Override working directory"
    ),
):
    """Global options for simple-agent."""
    settings_dict = {}
    if model:
        settings_dict["model_id"] = model
    if workdir:
        settings_dict["workdir"] = Path(workdir)

    ctx.obj = create_settings(**settings_dict) if settings_dict else None


@app.command("chat")
def chat_command(
    ctx: typer.Context,
):
    """Start interactive chat mode."""
    settings = ctx.obj or Settings()
    agent = _get_agent(settings)
    history = []

    console.print(f"[cyan]simple-agent[/cyan] - AI Agent at {settings.workdir}")
    console.print("Type 'exit' or 'quit' to end the session.\n")

    while True:
        try:
            query = typer.prompt("\n>>> ", prompt_suffix="")
        except (EOFError, KeyboardInterrupt):
            break

        if query.strip().lower() in ("q", "exit", "quit", ""):
            console.print("[yellow]Goodbye![/yellow]")
            break

        history.append({"role": "user", "content": query})

        with console.status("[bold green]Thinking...", spinner="dots"):
            try:
                agent_loop(history, agent)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

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
    agent = _get_agent(settings)

    if verbose:
        console.print(f"[cyan]Executing:[/cyan] {prompt}\n")

    history = [{"role": "user", "content": prompt}]

    with console.status("[bold green]Processing...", spinner="dots"):
        try:
            agent_loop(history, agent)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

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


def main_cli():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main_cli()
