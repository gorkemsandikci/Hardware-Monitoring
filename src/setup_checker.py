"""Environment setup checker for NVIDIA drivers, CUDA, PyTorch, and YOLOv8."""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Check if dependencies are installed
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
except ImportError:
    print("ERROR: Required dependencies are not installed.")
    print("\nPlease run: pip install -r requirements.txt")
    sys.exit(1)

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.gpu_utils import check_nvidia_smi, get_gpu_info
from src.utils.logger import setup_logger

logger = setup_logger(__name__)
console = Console()


class CheckResult:
    """Container for check result."""

    def __init__(self, name: str, status: str, message: str, recommendation: Optional[str] = None):
        """
        Initialize check result.

        Args:
            name: Check name
            status: Status (pass, fail, warning)
            message: Status message
            recommendation: Optional recommendation
        """
        self.name = name
        self.status = status  # 'pass', 'fail', 'warning'
        self.message = message
        self.recommendation = recommendation


def check_nvidia_driver() -> CheckResult:
    """
    Check NVIDIA driver installation.

    Returns:
        CheckResult with driver status
    """
    if not check_nvidia_smi():
        return CheckResult(
            name="NVIDIA Driver",
            status="fail",
            message="nvidia-smi not found. NVIDIA driver is not installed.",
            recommendation="Run: sudo ubuntu-drivers autoinstall\nThen reboot: sudo reboot",
        )

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return CheckResult(
                name="NVIDIA Driver",
                status="fail",
                message="nvidia-smi failed to query driver version",
                recommendation="Reinstall drivers: sudo ubuntu-drivers autoinstall",
            )

        driver_version = result.stdout.strip().split("\n")[0].strip()
        if not driver_version:
            return CheckResult(
                name="NVIDIA Driver",
                status="warning",
                message="Driver version could not be determined",
            )

        # Get CUDA version supported by driver
        cuda_result = subprocess.run(
            ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        cuda_version = None
        if cuda_result.returncode == 0:
            cuda_version = cuda_result.stdout.strip().split("\n")[0].strip()

        message = f"Driver version: {driver_version}"
        if cuda_version:
            message += f" | Supports CUDA: {cuda_version}"

        return CheckResult(
            name="NVIDIA Driver",
            status="pass",
            message=message,
        )

    except subprocess.TimeoutExpired:
        return CheckResult(
            name="NVIDIA Driver",
            status="fail",
            message="nvidia-smi command timed out",
        )
    except Exception as e:
        logger.error(f"Error checking NVIDIA driver: {e}")
        return CheckResult(
            name="NVIDIA Driver",
            status="fail",
            message=f"Error: {str(e)}",
        )


def check_cuda_toolkit() -> CheckResult:
    """
    Check CUDA toolkit installation.

    Returns:
        CheckResult with CUDA toolkit status
    """
    try:
        result = subprocess.run(
            ["nvcc", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return CheckResult(
                name="CUDA Toolkit",
                status="fail",
                message="nvcc not found. CUDA toolkit is not installed.",
                recommendation="Install CUDA toolkit from:\nhttps://docs.nvidia.com/cuda/cuda-installation-guide-linux/",
            )

        # Parse version from output
        output = result.stdout
        version_line = [line for line in output.split("\n") if "release" in line.lower()]
        if version_line:
            version_info = version_line[0]
            return CheckResult(
                name="CUDA Toolkit",
                status="pass",
                message=version_info.strip(),
            )
        else:
            return CheckResult(
                name="CUDA Toolkit",
                status="pass",
                message="CUDA toolkit installed (version could not be parsed)",
            )

    except FileNotFoundError:
        return CheckResult(
            name="CUDA Toolkit",
            status="fail",
            message="nvcc not found. CUDA toolkit is not installed.",
            recommendation="CUDA toolkit is optional. Install if needed for ML/AI development.\nSee docs/nvidia-setup.md for instructions.",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="CUDA Toolkit",
            status="fail",
            message="nvcc command timed out",
        )
    except Exception as e:
        logger.error(f"Error checking CUDA toolkit: {e}")
        return CheckResult(
            name="CUDA Toolkit",
            status="fail",
            message=f"Error: {str(e)}",
        )


def check_pytorch() -> Tuple[CheckResult, Optional[CheckResult]]:
    """
    Check PyTorch installation and CUDA support.

    Returns:
        Tuple of (PyTorch installation check, CUDA availability check)
    """
    # Check if PyTorch is installed
    try:
        import torch
        pytorch_version = torch.__version__
        pytorch_check = CheckResult(
            name="PyTorch",
            status="pass",
            message=f"PyTorch {pytorch_version} is installed",
        )
    except ImportError:
        pytorch_check = CheckResult(
            name="PyTorch",
            status="fail",
            message="PyTorch is not installed",
            recommendation="Install PyTorch with CUDA support:\npip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118",
        )
        return pytorch_check, None

    # Check CUDA availability
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
            cuda_version = torch.version.cuda

            message = f"CUDA available: Yes | Devices: {device_count} | Device 0: {device_name}"
            if cuda_version:
                message += f" | CUDA Version: {cuda_version}"

            cuda_check = CheckResult(
                name="PyTorch CUDA",
                status="pass",
                message=message,
            )
        else:
            cuda_check = CheckResult(
                name="PyTorch CUDA",
                status="warning",
                message="PyTorch CUDA is not available (CPU-only version installed)",
                recommendation="Reinstall PyTorch with CUDA support:\npip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118",
            )

        return pytorch_check, cuda_check

    except Exception as e:
        logger.error(f"Error checking PyTorch CUDA: {e}")
        cuda_check = CheckResult(
            name="PyTorch CUDA",
            status="fail",
            message=f"Error checking CUDA availability: {str(e)}",
        )
        return pytorch_check, cuda_check


def check_yolov8() -> CheckResult:
    """
    Check YOLOv8/Ultralytics installation.

    Returns:
        CheckResult with YOLOv8 status
    """
    try:
        import ultralytics

        version = getattr(ultralytics, "__version__", "Unknown")
        yolov8_check = CheckResult(
            name="YOLOv8/Ultralytics",
            status="pass",
            message=f"Ultralytics {version} is installed",
        )

        # Try to load a small model as validation
        try:
            from ultralytics import YOLO

            # This is just a validation - we won't actually load the model
            # to avoid downloading it unnecessarily
            yolov8_check.message += " | Package validated"
        except Exception as e:
            logger.warning(f"YOLOv8 validation warning: {e}")
            yolov8_check.message += f" | Warning: {str(e)}"

        return yolov8_check

    except ImportError:
        return CheckResult(
            name="YOLOv8/Ultralytics",
            status="fail",
            message="Ultralytics/YOLOv8 is not installed",
            recommendation="Install YOLOv8:\npip install ultralytics",
        )
    except Exception as e:
        logger.error(f"Error checking YOLOv8: {e}")
        return CheckResult(
            name="YOLOv8/Ultralytics",
            status="fail",
            message=f"Error: {str(e)}",
        )


def check_version_compatibility() -> List[CheckResult]:
    """
    Check version compatibility between driver, CUDA toolkit, and PyTorch.

    Returns:
        List of compatibility check results
    """
    results = []

    # Get driver CUDA version
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        driver_cuda = None
        if result.returncode == 0:
            driver_cuda = result.stdout.strip().split("\n")[0].strip()
    except:
        driver_cuda = None

    # Get toolkit CUDA version
    toolkit_cuda = None
    try:
        result = subprocess.run(
            ["nvcc", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "release" in line.lower():
                    # Extract version number
                    parts = line.split("release")
                    if len(parts) > 1:
                        version_part = parts[1].strip().split(",")[0]
                        toolkit_cuda = version_part.strip()
                    break
    except:
        pass

    # Get PyTorch CUDA version
    pytorch_cuda = None
    try:
        import torch

        if torch.cuda.is_available():
            pytorch_cuda = torch.version.cuda
    except:
        pass

    # Compare versions
    if driver_cuda and toolkit_cuda:
        try:
            driver_major = float(driver_cuda.split(".")[0] + "." + driver_cuda.split(".")[1])
            toolkit_major = float(toolkit_cuda.split(".")[0] + "." + toolkit_cuda.split(".")[1])

            if abs(driver_major - toolkit_major) > 0.1:
                results.append(
                    CheckResult(
                        name="Version Compatibility",
                        status="warning",
                        message=f"Driver CUDA ({driver_cuda}) and Toolkit CUDA ({toolkit_cuda}) versions differ",
                        recommendation="Ensure toolkit version is compatible with driver version",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="Version Compatibility",
                        status="pass",
                        message=f"Driver CUDA ({driver_cuda}) and Toolkit CUDA ({toolkit_cuda}) are compatible",
                    )
                )
        except:
            pass

    if pytorch_cuda and toolkit_cuda:
        try:
            pytorch_major = float(pytorch_cuda.split(".")[0] + "." + pytorch_cuda.split(".")[1])
            toolkit_major = float(toolkit_cuda.split(".")[0] + "." + toolkit_cuda.split(".")[1])

            if abs(pytorch_major - toolkit_major) > 0.1:
                results.append(
                    CheckResult(
                        name="PyTorch CUDA Compatibility",
                        status="warning",
                        message=f"PyTorch CUDA ({pytorch_cuda}) and Toolkit CUDA ({toolkit_cuda}) versions differ",
                        recommendation="Reinstall PyTorch with matching CUDA version",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="PyTorch CUDA Compatibility",
                        status="pass",
                        message=f"PyTorch CUDA ({pytorch_cuda}) matches Toolkit CUDA ({toolkit_cuda})",
                    )
                )
        except:
            pass

    return results


def display_results(results: List[CheckResult]):
    """
    Display check results in a formatted table.

    Args:
        results: List of check results
    """
    table = Table(title="Environment Setup Check Results", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan", width=20)
    table.add_column("Status", justify="center", width=15)
    table.add_column("Message", style="dim", width=45)
    table.add_column("Recommendation", style="yellow", width=50)

    for result in results:
        # Determine status color and symbol
        if result.status == "pass":
            status_text = "[bold green]✓ PASS[/bold green]"
        elif result.status == "warning":
            status_text = "[bold yellow]⚠ WARNING[/bold yellow]"
        else:
            status_text = "[bold red]✗ FAIL[/bold red]"

        recommendation = result.recommendation or ""
        table.add_row(result.name, status_text, result.message, recommendation)

    console.print("\n")
    console.print(table)
    console.print("")

    # Summary
    pass_count = sum(1 for r in results if r.status == "pass")
    warning_count = sum(1 for r in results if r.status == "warning")
    fail_count = sum(1 for r in results if r.status == "fail")

    summary_text = Text()
    summary_text.append("Summary: ", style="bold")
    summary_text.append(f"{pass_count} passed", style="green")
    if warning_count > 0:
        summary_text.append(f", {warning_count} warnings", style="yellow")
    if fail_count > 0:
        summary_text.append(f", {fail_count} failed", style="red")

    console.print(Panel(summary_text, title="[bold cyan]Check Summary[/bold cyan]", border_style="cyan"))


def main():
    """Main entry point for setup checker."""
    console.print("\n")
    console.print("[bold cyan]╔════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║   Environment Setup Checker                    ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════════════╝[/bold cyan]")
    console.print("")

    results = []

    # Check NVIDIA driver
    console.print("[dim]Checking NVIDIA driver...[/dim]")
    results.append(check_nvidia_driver())

    # Check CUDA toolkit
    console.print("[dim]Checking CUDA toolkit...[/dim]")
    results.append(check_cuda_toolkit())

    # Check PyTorch
    console.print("[dim]Checking PyTorch...[/dim]")
    pytorch_check, pytorch_cuda_check = check_pytorch()
    results.append(pytorch_check)
    if pytorch_cuda_check:
        results.append(pytorch_cuda_check)

    # Check YOLOv8
    console.print("[dim]Checking YOLOv8/Ultralytics...[/dim]")
    results.append(check_yolov8())

    # Check version compatibility
    console.print("[dim]Checking version compatibility...[/dim]")
    compatibility_results = check_version_compatibility()
    results.extend(compatibility_results)

    # Display results
    display_results(results)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Check cancelled by user[/yellow]\n")
        sys.exit(0)

