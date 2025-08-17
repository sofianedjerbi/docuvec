"""Enhanced logging configuration using rich library"""

import logging
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint


def setup_logger(
    name: str = "rag_etl",
    log_file: str = "data/etl.log",
    level: str = "INFO",
    rich_tracebacks: bool = True,
    show_path: bool = False,
    show_time: bool = True
) -> logging.Logger:
    """Setup enhanced logger with rich formatting
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        rich_tracebacks: Whether to use rich tracebacks
        show_path: Whether to show file path in logs
        show_time: Whether to show time in console logs
        
    Returns:
        Configured logger instance
    """
    # Ensure log directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Rich console handler with colors and formatting
    console = Console()
    rich_handler = RichHandler(
        console=console,
        show_time=show_time,
        show_path=show_path,
        rich_tracebacks=rich_tracebacks,
        tracebacks_show_locals=rich_tracebacks,
        markup=True,
        log_time_format="[%H:%M:%S]"
    )
    
    # Custom format for rich handler
    rich_handler.setFormatter(logging.Formatter(
        "%(message)s",
        datefmt="[%X]"
    ))
    
    logger.addHandler(rich_handler)
    
    # File handler (standard formatting)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_console() -> Console:
    """Get a rich console instance for direct output
    
    Returns:
        Rich Console instance
    """
    return Console()


def log_section(title: str, subtitle: str = None):
    """Display a formatted section header
    
    Args:
        title: Section title
        subtitle: Optional subtitle
    """
    console = get_console()
    
    if subtitle:
        panel_content = Text(title, style="bold blue") + "\n" + Text(subtitle, style="dim")
    else:
        panel_content = Text(title, style="bold blue")
    
    console.print(Panel(
        panel_content,
        expand=True,
        border_style="cyan",
        padding=(1, 2)
    ))


def log_subsection(title: str):
    """Display a formatted subsection header
    
    Args:
        title: Subsection title
    """
    console = get_console()
    console.print(f"\n[bold yellow]▸ {title}[/bold yellow]")


def log_stats(stats: dict, title: str = "Statistics"):
    """Display statistics in a formatted table
    
    Args:
        stats: Dictionary of statistics
        title: Title for the stats section
    """
    console = get_console()
    
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Value", style="green", justify="right")
    
    for key, value in stats.items():
        # Format value based on type
        if isinstance(value, float):
            formatted_value = f"{value:,.2f}"
        elif isinstance(value, int):
            formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        
        table.add_row(key, formatted_value)
    
    console.print(table)


def log_progress(description: str, current: int, total: int):
    """Display a progress indicator
    
    Args:
        description: Progress description
        current: Current item number
        total: Total items
    """
    console = get_console()
    percentage = (current / total) * 100 if total > 0 else 0
    
    # Create progress bar
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    
    console.print(
        f"[cyan]{description}[/cyan] "
        f"[yellow]{bar}[/yellow] "
        f"[green]{current}/{total}[/green] "
        f"[dim]({percentage:.1f}%)[/dim]",
        end="\r" if current < total else "\n"
    )


def log_success(message: str):
    """Log a success message with formatting
    
    Args:
        message: Success message
    """
    console = get_console()
    console.print(f"[bold green]✓[/bold green] {message}")


def log_warning(message: str):
    """Log a warning message with formatting
    
    Args:
        message: Warning message
    """
    console = get_console()
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def log_error(message: str):
    """Log an error message with formatting
    
    Args:
        message: Error message
    """
    console = get_console()
    console.print(f"[bold red]✗[/bold red] {message}")


def log_info(message: str):
    """Log an info message with formatting
    
    Args:
        message: Info message
    """
    console = get_console()
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def log_debug(message: str):
    """Log a debug message with formatting
    
    Args:
        message: Debug message
    """
    console = get_console()
    console.print(f"[dim]🔍 {message}[/dim]")