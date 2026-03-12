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
from simple_agent.utils.logger import setup_logger

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
    log_level: str = typer.Option("INFO", "--log-level", help="Set logging level (DEBUG, INFO, WARNING, ERROR)"),
):
    """Global options for simple-agent."""
    settings_dict = {}
    if model:
        settings_dict["model_id"] = model
    if provider:
        settings_dict["provider"] = provider
    if workdir:
        settings_dict["workdir"] = Path(workdir)

    # Initialize settings
    settings = create_settings(**settings_dict) if settings_dict else Settings()
    ctx.obj = settings

    # Setup logging
    setup_logger(
        log_dir=settings.logs_dir,
        log_level=log_level,
        enable_console=True,
        enable_file=True,
    )


@app.command("chat")
def chat_command(
    ctx: typer.Context,
    resume: str = typer.Option(None, "--resume", "-r", help="Resume from session ID"),
):
    """Start interactive chat mode."""
    import time
    settings = ctx.obj or Settings()

    # Create permission manager with status controller
    status_controller = ConsoleStatusController(console)
    permission_manager = PermissionManager(status_controller=status_controller)

    agent = _get_agent(settings, permission_manager)

    # Initialize project and session
    from simple_agent.managers.project import ProjectManager
    from simple_agent.managers.session import SessionManager
    from simple_agent.models.projects import SessionMessage

    pm = ProjectManager(settings)
    sm = SessionManager(settings)

    # Get or create project
    project = pm.get_or_create_project(settings.workdir)
    pm.set_current_project(project)

    # Resume session or create new one
    if resume:
        session = sm.get_session(project.project_id, resume)
        if not session:
            console.print(f"[red]Session '{resume}' not found.[/red]")
            raise typer.Exit(1)
        # Load session history
        saved_messages = sm.read_messages(project.project_id, session.session_id)
        history = []
        for msg in saved_messages:
            history.append({"role": msg.role, "content": msg.content})
    else:
        session = sm.create_session(project.project_id, title="Chat Session")
        sm.set_current_session(session)
        history = []

    provider_name = settings.get_active_provider()
    console.print(f"[cyan]simple-agent[/cyan] - AI Agent at {settings.workdir}")
    console.print(f"Provider: [green]{provider_name}[/green] | Model: [yellow]{settings.model_id or 'default'}[/yellow]")
    console.print(f"Session: [cyan]{session.session_id[:8]}...[/cyan]" + (f" (resumed)" if resume else ""))
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

        # Save user message to session
        user_msg = SessionMessage(
            role="user",
            content=query,
            timestamp=time.time()
        )
        sm.append_message(project.project_id, session.session_id, user_msg)

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

        # Display response and save to session
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
                        # Save assistant message to session
                        assistant_msg = SessionMessage(
                            role="assistant",
                            content=response,
                            timestamp=time.time()
                        )
                        sm.append_message(project.project_id, session.session_id, assistant_msg)
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


# ============================================================================
# Project Management Commands
# ============================================================================

@app.command("project-list")
def project_list_command(ctx: typer.Context):
    """List all projects."""
    settings = ctx.obj or Settings()
    from simple_agent.managers.project import ProjectManager

    pm = ProjectManager(settings)
    projects = pm.list_projects()

    if not projects:
        console.print("[yellow]No projects found.[/yellow]")
        return

    console.print("\n[bold]Projects:[/bold]\n")
    for p in projects:
        console.print(f"  [cyan]{p.project_id}[/cyan]")
        console.print(f"    Path: {p.original_path}")
        console.print(f"    Sessions: {p.session_count}")
        console.print(f"    Last accessed: {p.last_accessed.strftime('%Y-%m-%d %H:%M')}")
        console.print()


@app.command("project-info")
def project_info_command(
    ctx: typer.Context,
    project_id: str = typer.Argument(None, help="Project ID (defaults to current)"),
):
    """Show project details."""
    settings = ctx.obj or Settings()
    from simple_agent.managers.project import ProjectManager

    pm = ProjectManager(settings)

    # Use current project if no ID provided
    if not project_id:
        current = pm.get_current_project()
        if not current:
            console.print("[yellow]No current project. Use --project-id or specify a project.[/yellow]")
            return
        project_id = current.project_id

    project = pm.get_project(project_id)
    if not project:
        console.print(f"[red]Project '{project_id}' not found.[/red]")
        return

    console.print(f"\n[bold]Project: {project.project_id}[/bold]\n")
    console.print(f"  Path: {project.original_path}")
    console.print(f"  Sessions: {project.session_count}")
    console.print(f"  Created: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"  Last accessed: {project.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}")


# ============================================================================
# Session Management Commands
# ============================================================================

@app.command("session-list")
def session_list_command(
    ctx: typer.Context,
    project_id: str = typer.Option(None, "--project", "-p", help="Project ID (defaults to current)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum sessions to show"),
):
    """List sessions for a project."""
    settings = ctx.obj or Settings()
    from simple_agent.managers.project import ProjectManager
    from simple_agent.managers.session import SessionManager

    pm = ProjectManager(settings)
    sm = SessionManager(settings)

    # Use current project if no ID provided
    if not project_id:
        current = pm.get_current_project()
        if not current:
            console.print("[yellow]No current project. Use --project or specify a project.[/yellow]")
            return
        project_id = current.project_id

    sessions = sm.list_sessions(project_id, limit=limit)

    if not sessions:
        console.print(f"[yellow]No sessions found for project '{project_id}'.[/yellow]")
        return

    console.print(f"\n[bold]Sessions for {project_id}:[/bold]\n")
    for s in sessions:
        status_icon = "[green]*[/green]" if s.status == "active" else "[dim]-[/dim]"
        title = s.title or "(no title)"
        console.print(f"  {status_icon} [cyan]{s.session_id[:8]}...[/cyan] {title}")
        console.print(f"    Messages: {s.message_count}")
        console.print(f"    Created: {s.created_at.strftime('%Y-%m-%d %H:%M')}")
        if s.parent_session_id:
            console.print(f"    Parent: {s.parent_session_id[:8]}...")
        console.print()


@app.command("session-show")
def session_show_command(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Session ID"),
    project_id: str = typer.Option(None, "--project", "-p", help="Project ID (defaults to current)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of messages to show"),
):
    """Show session history."""
    settings = ctx.obj or Settings()
    from simple_agent.managers.project import ProjectManager
    from simple_agent.managers.session import SessionManager

    pm = ProjectManager(settings)
    sm = SessionManager(settings)

    # Use current project if no ID provided
    if not project_id:
        current = pm.get_current_project()
        if not current:
            console.print("[yellow]No current project. Use --project or specify a project.[/yellow]")
            return
        project_id = current.project_id

    session = sm.get_session(project_id, session_id)
    if not session:
        console.print(f"[red]Session '{session_id}' not found.[/red]")
        return

    messages = sm.read_messages(project_id, session_id, limit=limit)

    console.print(f"\n[bold]Session: {session_id[:8]}...[/bold]")
    if session.title:
        console.print(f"Title: {session.title}")
    console.print(f"Messages: {session.message_count} (showing last {len(messages)})\n")

    for msg in messages:
        role_color = "green" if msg.role == "user" else "blue"
        console.print(f"[{role_color}]{msg.role}:[/{role_color}] {msg.content[:200]}...")
        console.print()


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
