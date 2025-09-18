"""Modern CLI progress display using rich."""

from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    SpinnerColumn,
)
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from typing import Dict, Any, Optional, List
import time
from contextlib import contextmanager


class ModernCLI:
    """Modern, minimalistic CLI interface with rich formatting."""

    def __init__(self):
        self.console = Console()
        self.start_time: Optional[float] = None

    def _format_hours(self, total_hours: float) -> str:
        """Format decimal hours into Jira-style duration (e.g., 2h 30m)."""
        if total_hours == 0:
            return "0m"

        hours = int(total_hours)
        minutes = int((total_hours - hours) * 60)

        if hours == 0:
            return f"{minutes}m"
        elif minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {minutes}m"

    def show_banner(self) -> None:
        """Show application banner."""
        banner = Text("jira2solidtime", style="bold blue")
        banner.append(" • Tempo ↔ Solidtime Sync", style="dim")
        self.console.print(Panel(banner, border_style="blue"))

    def validate_config(self, errors: List[str]) -> bool:
        """Show configuration validation results."""
        if errors:
            self.console.print("❌ [red bold]Configuration Error[/red bold]")
            for error in errors:
                self.console.print(f"   • {error}", style="red")
            return False
        else:
            self.console.print("✅ [green]Configuration validated[/green]", end="")
            return True

    def validate_apis(self, api_results: Dict[str, Any]) -> bool:
        """Show API connectivity validation results."""
        all_good = True
        error_messages = []

        for service, result in api_results.items():
            if result["success"]:
                continue
            else:
                all_good = False
                error_messages.append(f"{service}: {result['error']}")

        if all_good:
            self.console.print(" • [green]APIs connected[/green]")
            return True
        else:
            self.console.print("\n❌ [red bold]API Connectivity Failed[/red bold]")
            for error in error_messages:
                self.console.print(f"   • {error}", style="red")
            return False

    def start_sync(self, time_range: str, dry_run: bool = False) -> None:
        """Start sync operation display."""
        self.start_time = time.time()

        mode_text = "[yellow]DRY RUN[/yellow]" if dry_run else "[blue]Syncing[/blue]"
        self.console.print(f"\n⏳ {mode_text} [cyan]{time_range}[/cyan]...")

    def complete_sync(
        self,
        time_range: str,
        results: Dict[str, Any],
        dry_run: bool = False,
        project_keys: Optional[List[str]] = None,
    ) -> None:
        """Show sync completion summary."""
        if self.start_time is None:
            duration = 0.0
        else:
            duration = time.time() - self.start_time

        # Extract results
        total_entries = results.get("total_entries", 0)
        changes = results.get("changes", 0)
        total_hours = results.get("total_hours", 0.0)

        # Format changes text
        if changes == 0:
            changes_text = "[green]up-to-date[/green]"
        else:
            changes_text = f"[yellow]{changes} changes[/yellow]"

        # Format project info
        project_info = ""
        if project_keys:
            project_names = ", ".join(project_keys)
            project_info = f" • [magenta]{project_names}[/magenta]"

        # Success indicator
        status_icon = "🔍" if dry_run else "✅"

        # Summary line
        summary = (
            f"{status_icon} [green bold]{duration:.2f}s[/green bold] • "
            f"[cyan]{time_range}[/cyan]{project_info} • "
            f"[white]{total_entries} entries[/white] • "
            f"{changes_text} • "
            f"[blue]{self._format_hours(total_hours)} total[/blue]"
        )

        # Show detailed results if not dry run and changes were made
        if not dry_run and changes > 0:
            self._show_detailed_results(results)

        # Show framed summary
        self.console.print(Panel(summary, border_style="green", title="Sync Summary"))

    def show_error(self, error: str) -> None:
        """Show error message."""
        self.console.print(f"\n❌ [red bold]Error:[/red bold] {error}")

    def show_warning(self, message: str) -> None:
        """Show warning message."""
        self.console.print(f"⚠️  [yellow]{message}[/yellow]")

    def _show_detailed_results(self, results: Dict[str, Any]) -> None:
        """Show detailed sync results with entry details."""
        worklog_details = results.get("worklog_details", {})

        # Show operations summary (unused variables removed)

        # Show detailed table for each operation type
        self._show_operation_table(
            "Created", worklog_details.get("created", []), "green"
        )
        self._show_operation_table(
            "Updated", worklog_details.get("updated", []), "yellow"
        )
        self._show_operation_table("Deleted", worklog_details.get("deleted", []), "red")

    def _show_operation_table(self, operation: str, entries: list, color: str) -> None:
        """Show a table for a specific operation type."""
        if not entries:
            return

        self.console.print(f"\n[{color} bold]{operation}:[/{color} bold]")

        # Create table with proper column widths for 120 char terminal
        table = Table(show_header=True, box=None, width=120)
        table.add_column("Issue", width=8, style="cyan")
        table.add_column("Summary", width=40, overflow="ellipsis")
        table.add_column("Description", width=55, overflow="ellipsis", style="dim")
        table.add_column("Duration", width=10, justify="right", style="blue")

        for entry in entries:
            issue_key = entry.get("issue_key", "")
            summary = entry.get("summary", "")[:40]  # Truncate to fit
            description = entry.get("description", "")[:55]  # Truncate to fit
            duration_hours = entry.get("duration_hours", 0.0)
            duration_formatted = self._format_hours(duration_hours)

            # Handle UPDATE operations with change visualization
            if operation == "Updated":
                # Check for changes and apply styling
                description_changed = entry.get("description_changed", False)
                duration_changed = entry.get("duration_changed", False)
                old_duration_hours = entry.get("old_duration_hours")

                # Format duration with old -> new if changed
                if duration_changed and old_duration_hours is not None:
                    old_duration_formatted = self._format_hours(old_duration_hours)
                    duration_formatted = (
                        f"{old_duration_formatted} → {duration_formatted}"
                    )

                # Apply yellow styling for changed fields
                description_style = "yellow" if description_changed else "dim"
                duration_style = "yellow" if duration_changed else "blue"

                table.add_row(
                    issue_key,
                    summary,
                    Text(description, style=description_style),
                    Text(duration_formatted, style=duration_style),
                )
            else:
                table.add_row(issue_key, summary, description, duration_formatted)

        self.console.print(table)

    def format_time_range(self, from_date: str, to_date: str) -> str:
        """Format time range for display."""
        if from_date == to_date:
            return from_date

        # Check if it's a full month
        from_parts = from_date.split("-")
        to_parts = to_date.split("-")

        if (
            len(from_parts) == 3
            and len(to_parts) == 3
            and from_parts[0] == to_parts[0]
            and from_parts[1] == to_parts[1]
            and from_parts[2] == "01"
        ):
            # Check if to_date is last day of month (approximate)
            if int(to_parts[2]) >= 28:
                return f"{from_parts[0]}-{from_parts[1]}"

        return f"{from_date}..{to_date}"

    def ask_confirmation(self, message: str) -> bool:
        """Ask for user confirmation."""
        response = self.console.input(f"❓ {message} [y/N]: ")
        return response.lower().startswith("y")

    @contextmanager
    def progress_spinner(self, description: str):
        """Context manager for showing a spinner with description."""
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task(description, total=None)
            try:
                yield progress
            finally:
                progress.remove_task(task)
