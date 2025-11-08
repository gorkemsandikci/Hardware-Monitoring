"""Main menu for hardware monitoring tools."""

import sys
import subprocess
from pathlib import Path

# Check if dependencies are installed
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
    from rich import box
except ImportError:
    print("ERROR: Required dependencies are not installed.")
    print("\nPlease run the following commands:")
    print("  1. cd /home/gorkem/dev/personal/hardware-monitoring")
    print("  2. source .venv/bin/activate")
    print("  3. pip install -r requirements.txt")
    sys.exit(1)

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)
console = Console()


def show_menu():
    """Display the main menu."""
    menu_text = Text()
    menu_text.append("Hardware Monitor System\n\n", style="bold cyan")
    menu_text.append("Select an option:\n\n", style="bold")
    menu_text.append("  1. ", style="yellow")
    menu_text.append("Hardware Inventory", style="green")
    menu_text.append(" - Collect and display system hardware info\n", style="dim")
    
    menu_text.append("  2. ", style="yellow")
    menu_text.append("Real-time Monitoring", style="green")
    menu_text.append(" - Live dashboard with system metrics\n", style="dim")
    
    menu_text.append("  3. ", style="yellow")
    menu_text.append("Environment Checker", style="green")
    menu_text.append(" - Validate NVIDIA/CUDA/PyTorch setup\n", style="dim")
    
    menu_text.append("  4. ", style="yellow")
    menu_text.append("Quick Driver Check", style="green")
    menu_text.append(" - Check NVIDIA driver status\n", style="dim")
    
    menu_text.append("  5. ", style="yellow")
    menu_text.append("Web Server", style="green")
    menu_text.append(" - Start web server for remote monitoring\n", style="dim")
    
    menu_text.append("\n  ", style="dim")
    menu_text.append("q", style="red")
    menu_text.append(" - Quit\n", style="dim")

    panel = Panel(
        menu_text,
        title="[bold cyan]Main Menu[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)


def run_inventory():
    """Run hardware inventory."""
    console.print("\n[bold green]Running Hardware Inventory...[/bold green]\n")
    try:
        script_path = Path(__file__).parent / "inventory.py"
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running inventory: {e}[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")


def run_monitor():
    """Run real-time monitoring dashboard."""
    console.print("\n[bold green]Starting Real-time Monitoring Dashboard...[/bold green]")
    console.print("[dim]Press 'q' in the monitor to quit[/dim]\n")
    try:
        script_path = Path(__file__).parent / "monitor.py"
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running monitor: {e}[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped[/yellow]")


def run_setup_checker():
    """Run environment setup checker."""
    console.print("\n[bold green]Running Environment Setup Checker...[/bold green]\n")
    try:
        script_path = Path(__file__).parent / "setup_checker.py"
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running setup checker: {e}[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")


def run_driver_check():
    """Run quick driver check."""
    console.print("\n[bold green]Checking NVIDIA Drivers...[/bold green]\n")
    try:
        script_path = Path(__file__).parent.parent / "scripts" / "check-drivers.sh"
        subprocess.run(["bash", str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running driver check: {e}[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")


def run_web_server():
    """Run web server for remote monitoring."""
    console.print("\n[bold green]Starting Web Server...[/bold green]")
    console.print("[dim]The server will be accessible from any device on your network[/dim]\n")
    
    try:
        script_path = Path(__file__).parent / "web_server.py"
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running web server: {e}[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Web server stopped[/yellow]")


def main():
    """Main menu loop."""
    console.print("\n")
    console.print("[bold cyan]╔════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║   Hardware Monitor System v1.0.0     ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════╝[/bold cyan]")
    console.print("")

    while True:
        show_menu()
        
        choice = Prompt.ask(
            "\n[bold cyan]Enter your choice[/bold cyan]",
            choices=["1", "2", "3", "4", "5", "q", "Q"],
            default="q",
        ).lower()

        if choice == "1":
            run_inventory()
        elif choice == "2":
            run_monitor()
        elif choice == "3":
            run_setup_checker()
        elif choice == "4":
            run_driver_check()
        elif choice == "5":
            run_web_server()
        elif choice == "q":
            console.print("\n[bold yellow]Goodbye![/bold yellow]\n")
            break

        # Wait for user to continue
        if choice != "q":
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Goodbye![/bold yellow]\n")
        sys.exit(0)

