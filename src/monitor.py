"""Real-time hardware monitoring dashboard with terminal UI."""

import signal
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Check if dependencies are installed
try:
    import psutil
    from rich.console import Console
except ImportError as e:
    print("ERROR: Required dependencies are not installed.")
    print(f"Missing: {e.name if hasattr(e, 'name') else 'unknown module'}")
    print("\nPlease run the following commands:")
    print("  1. cd /home/gorkem/dev/personal/hardware-monitoring")
    print("  2. source .venv/bin/activate")
    print("  3. pip install -r requirements.txt")
    print("\nOr use the setup script:")
    print("  ./scripts/setup-venv.sh")
    sys.exit(1)
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.gpu_utils import get_gpu_metrics, get_gpu_info
from src.utils.logger import setup_logger
from src.utils.format_utils import (
    format_bytes,
    format_percentage,
    format_temperature,
    format_frequency,
)

logger = setup_logger(__name__)
console = Console()


class MonitorDashboard:
    """Real-time hardware monitoring dashboard."""

    def __init__(self, update_interval: float = 1.0):
        """
        Initialize monitoring dashboard.

        Args:
            update_interval: Update interval in seconds (default: 1.0)
        """
        self.update_interval = update_interval
        self.running = True
        self.reset_stats()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals."""
        self.running = False
        console.print("\n[bold yellow]Shutting down...[/bold yellow]")
        sys.exit(0)

    def reset_stats(self):
        """Reset statistics counters."""
        self.start_time = time.time()
        logger.info("Statistics reset")

    def get_cpu_table(self) -> Table:
        """Get CPU monitoring table."""
        table = Table(title="CPU", show_header=True, header_style="bold magenta")
        table.add_column("Core", style="cyan", no_wrap=True)
        table.add_column("Usage %", justify="right")
        table.add_column("Status", justify="center")

        try:
            per_cpu = psutil.cpu_percent(percpu=True, interval=0.1)
            for i, usage in enumerate(per_cpu):
                status = self._get_status_color(usage, 70, 90)
                table.add_row(
                    f"Core {i}",
                    format_percentage(usage),
                    f"[{status}]{self._get_status_symbol(usage, 70, 90)}[/{status}]",
                )

            # Overall CPU usage
            overall = psutil.cpu_percent(interval=0.1)
            status = self._get_status_color(overall, 70, 90)
            table.add_row(
                "[bold]Overall[/bold]",
                f"[bold]{format_percentage(overall)}[/bold]",
                f"[bold {status}]{self._get_status_symbol(overall, 70, 90)}[/bold {status}]",
            )

            # CPU frequency
            try:
                freq = psutil.cpu_freq()
                if freq:
                    table.add_row(
                        "[bold]Frequency[/bold]",
                        format_frequency(freq.current * 1e6),
                        "",
                    )
            except:
                pass

        except Exception as e:
            logger.error(f"Error getting CPU info: {e}")
            table.add_row("Error", "N/A", "")

        return table

    def get_memory_table(self) -> Table:
        """Get memory monitoring table."""
        table = Table(title="Memory", show_header=True, header_style="bold blue")
        table.add_column("Type", style="cyan")
        table.add_column("Used", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Usage %", justify="right")
        table.add_column("Status", justify="center")

        try:
            memory = psutil.virtual_memory()
            status = self._get_status_color(memory.percent, 80, 90)
            table.add_row(
                "RAM",
                format_bytes(memory.used),
                format_bytes(memory.total),
                format_percentage(memory.percent),
                f"[{status}]{self._get_status_symbol(memory.percent, 80, 90)}[/{status}]",
            )

            swap = psutil.swap_memory()
            status = self._get_status_color(swap.percent, 80, 90)
            table.add_row(
                "Swap",
                format_bytes(swap.used),
                format_bytes(swap.total),
                format_percentage(swap.percent),
                f"[{status}]{self._get_status_symbol(swap.percent, 80, 90)}[/{status}]",
            )

        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            table.add_row("Error", "N/A", "N/A", "N/A", "")

        return table

    def get_disk_table(self) -> Table:
        """Get disk monitoring table."""
        table = Table(title="Disk I/O", show_header=True, header_style="bold green")
        table.add_column("Device", style="cyan")
        table.add_column("Mount", style="dim")
        table.add_column("Used", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Usage %", justify="right")
        table.add_column("Status", justify="center")

        try:
            partitions = psutil.disk_partitions()
            for partition in partitions[:5]:  # Limit to 5 partitions
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    status = self._get_status_color(usage.percent, 80, 90)
                    table.add_row(
                        partition.device,
                        partition.mountpoint,
                        format_bytes(usage.used),
                        format_bytes(usage.total),
                        format_percentage(usage.percent),
                        f"[{status}]{self._get_status_symbol(usage.percent, 80, 90)}[/{status}]",
                    )
                except PermissionError:
                    continue
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error getting disk info: {e}")
            table.add_row("Error", "N/A", "N/A", "N/A", "N/A", "")

        return table

    def get_network_table(self) -> Table:
        """Get network monitoring table."""
        table = Table(title="Network", show_header=True, header_style="bold yellow")
        table.add_column("Interface", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Sent", justify="right")
        table.add_column("Recv", justify="right")
        table.add_column("Speed", justify="right")

        try:
            net_io = psutil.net_io_counters(pernic=True)
            net_if_stats = psutil.net_if_stats()

            for interface_name, stats in list(net_if_stats.items())[
                :5
            ]:  # Limit to 5 interfaces
                if interface_name == "lo":
                    continue

                is_up = "UP" if stats.isup else "DOWN"
                status_color = "green" if stats.isup else "red"

                # Get network I/O stats for this interface
                if_stats = net_io.get(interface_name)
                sent = if_stats.bytes_sent if if_stats else 0
                recv = if_stats.bytes_recv if if_stats else 0

                speed = f"{stats.speed} Mbps" if stats.speed > 0 else "N/A"

                table.add_row(
                    interface_name,
                    f"[{status_color}]{is_up}[/{status_color}]",
                    format_bytes(sent),
                    format_bytes(recv),
                    speed,
                )

        except Exception as e:
            logger.error(f"Error getting network info: {e}")
            table.add_row("Error", "N/A", "N/A", "N/A", "N/A")

        return table

    def get_gpu_table(self) -> Optional[Table]:
        """Get GPU monitoring table."""
        try:
            _, _, gpus = get_gpu_info()
            if not gpus:
                return None

            table = Table(title="GPU", show_header=True, header_style="bold red")
            table.add_column("GPU", style="cyan")
            table.add_column("Utilization %", justify="right")
            table.add_column("Temperature", justify="right")
            table.add_column("Memory", justify="right")
            table.add_column("Power", justify="right")
            table.add_column("Status", justify="center")

            for gpu in gpus:
                metrics = get_gpu_metrics(gpu.index)
                if metrics:
                    util = metrics.get("utilization", 0)
                    temp = metrics.get("temperature")
                    mem_used = metrics.get("memory_used", 0)
                    mem_total = metrics.get("memory_total", 0)
                    mem_percent = metrics.get("memory_percent", 0)
                    power = metrics.get("power")

                    status = self._get_status_color(util, 80, 95)

                    temp_str = format_temperature(temp) if temp is not None else "N/A"
                    power_str = f"{power:.1f} W" if power is not None else "N/A"
                    mem_str = f"{format_bytes(mem_used)} / {format_bytes(mem_total)}"

                    table.add_row(
                        f"{gpu.name}",
                        format_percentage(util),
                        temp_str,
                        mem_str,
                        power_str,
                        f"[{status}]{self._get_status_symbol(util, 80, 95)}[/{status}]",
                    )
                else:
                    table.add_row(
                        f"{gpu.name}",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        "[yellow]?[/yellow]",
                    )

            return table

        except Exception as e:
            logger.error(f"Error getting GPU info: {e}")
            return None

    def _get_status_color(
        self, value: float, warning_threshold: float, critical_threshold: float
    ) -> str:
        """
        Get status color based on value and thresholds.

        Args:
            value: Value to check
            warning_threshold: Warning threshold
            critical_threshold: Critical threshold

        Returns:
            Color name (green, yellow, red)
        """
        if value >= critical_threshold:
            return "red"
        elif value >= warning_threshold:
            return "yellow"
        else:
            return "green"

    def _get_status_symbol(
        self, value: float, warning_threshold: float, critical_threshold: float
    ) -> str:
        """
        Get status symbol based on value and thresholds.

        Args:
            value: Value to check
            warning_threshold: Warning threshold
            critical_threshold: Critical threshold

        Returns:
            Status symbol (✓, ⚠, ✗)
        """
        if value >= critical_threshold:
            return "✗"
        elif value >= warning_threshold:
            return "⚠"
        else:
            return "✓"

    def create_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()

        # Create panels
        cpu_panel = Panel(self.get_cpu_table(), border_style="magenta")
        memory_panel = Panel(self.get_memory_table(), border_style="blue")
        disk_panel = Panel(self.get_disk_table(), border_style="green")
        network_panel = Panel(self.get_network_table(), border_style="yellow")

        # Create GPU panel if available
        gpu_table = self.get_gpu_table()
        if gpu_table:
            gpu_panel = Panel(gpu_table, border_style="red")
        else:
            gpu_panel = Panel(
                Text("No NVIDIA GPUs detected", style="dim"), border_style="red"
            )

        # Create info panel
        uptime = time.time() - self.start_time
        uptime_str = (
            f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
        )
        info_text = Text()
        info_text.append(
            "Hardware Monitor - Press 'q' to quit, 'r' to reset stats\n", style="bold"
        )
        info_text.append(f"Uptime: {uptime_str}\n", style="dim")
        info_text.append(f"Update Interval: {self.update_interval}s", style="dim")
        info_panel = Panel(info_text, border_style="cyan", title="Info")

        # Split layout
        layout.split_column(
            Layout(info_panel, size=3),
            Layout(name="main"),
        )

        layout["main"].split_row(
            Layout(cpu_panel, name="left"),
            Layout(name="right"),
        )

        layout["right"].split_column(
            Layout(memory_panel, name="top_right"),
            Layout(name="bottom_right"),
        )

        layout["bottom_right"].split_row(
            Layout(disk_panel, name="bottom_left"),
            Layout(name="bottom_right_col"),
        )

        layout["bottom_right_col"].split_column(
            Layout(network_panel),
            Layout(gpu_panel),
        )

        return layout

    def run(self):
        """Run the monitoring dashboard."""
        console.print("[bold green]Starting hardware monitor...[/bold green]")
        console.print("[dim]Press 'q' to quit, 'r' to reset stats[/dim]\n")

        try:
            with Live(
                self.create_layout(),
                refresh_per_second=1.0 / self.update_interval,
                screen=True,
            ) as live:
                while self.running:
                    live.update(self.create_layout())
                    time.sleep(self.update_interval)

                    # Check for keyboard input (non-blocking)
                    # Note: This is a simplified version. For better keyboard handling,
                    # consider using keyboard library or threading
                    try:
                        import select

                        if select.select([sys.stdin], [], [], 0)[0]:
                            key = sys.stdin.read(1)
                            if key.lower() == "q":
                                break
                            elif key.lower() == "r":
                                self.reset_stats()
                    except:
                        pass  # Non-blocking input not available on all systems

        except KeyboardInterrupt:
            pass
        finally:
            console.print("\n[bold yellow]Monitor stopped.[/bold yellow]")


def main() -> None:
    """Main entry point for monitor script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Real-time hardware monitoring dashboard"
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=1.0,
        help="Update interval in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    dashboard = MonitorDashboard(update_interval=args.interval)
    dashboard.run()


if __name__ == "__main__":
    main()
