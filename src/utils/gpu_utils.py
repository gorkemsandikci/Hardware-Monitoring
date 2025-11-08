"""GPU-specific utilities for NVIDIA GPU detection and monitoring."""

import subprocess
import logging
from typing import Dict, List, Optional, Tuple

try:
    import pynvml

    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

logger = logging.getLogger(__name__)


class GPUInfo:
    """Container for GPU information."""

    def __init__(
        self,
        name: str,
        driver_version: str,
        cuda_version: Optional[str],
        total_memory: int,
        index: int = 0,
    ):
        """
        Initialize GPU information.

        Args:
            name: GPU model name
            driver_version: NVIDIA driver version
            cuda_version: Supported CUDA version (from driver)
            total_memory: Total VRAM in bytes
            index: GPU index
        """
        self.name = name
        self.driver_version = driver_version
        self.cuda_version = cuda_version
        self.total_memory = total_memory
        self.index = index


def check_nvidia_smi() -> bool:
    """
    Check if nvidia-smi command is available.

    Returns:
        True if nvidia-smi is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def get_gpu_info_nvidia_smi() -> Tuple[Optional[str], Optional[str], List[GPUInfo]]:
    """
    Get GPU information using nvidia-smi subprocess calls.

    Returns:
        Tuple of (driver_version, cuda_version, list_of_gpu_info)
        Returns (None, None, []) if nvidia-smi fails
    """
    if not check_nvidia_smi():
        logger.warning("nvidia-smi not available")
        return None, None, []

    try:
        # Get driver and CUDA version
        version_result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=driver_version,cuda_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if version_result.returncode != 0:
            logger.error(f"nvidia-smi version query failed: {version_result.stderr}")
            return None, None, []

        # Get GPU details
        gpu_result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if gpu_result.returncode != 0:
            logger.error(f"nvidia-smi GPU query failed: {gpu_result.stderr}")
            return None, None, []

        # Parse driver and CUDA version (from first GPU)
        version_lines = version_result.stdout.strip().split("\n")
        if version_lines:
            first_line = version_lines[0].strip()
            parts = [p.strip() for p in first_line.split(",")]
            if len(parts) >= 2:
                driver_version = parts[0]
                cuda_version = parts[1] if parts[1] else None
            else:
                driver_version = None
                cuda_version = None
        else:
            driver_version = None
            cuda_version = None

        # Parse GPU information
        gpus = []
        gpu_lines = gpu_result.stdout.strip().split("\n")
        for line in gpu_lines:
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                try:
                    index = int(parts[0])
                    name = parts[1]
                    memory_mb = int(parts[2])
                    memory_bytes = memory_mb * 1024 * 1024
                    gpus.append(
                        GPUInfo(
                            name=name,
                            driver_version=driver_version or "Unknown",
                            cuda_version=cuda_version,
                            total_memory=memory_bytes,
                            index=index,
                        )
                    )
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse GPU line '{line}': {e}")
                    continue

        return driver_version, cuda_version, gpus

    except subprocess.TimeoutExpired:
        logger.error("nvidia-smi command timed out")
        return None, None, []
    except Exception as e:
        logger.error(f"Error getting GPU info via nvidia-smi: {e}")
        return None, None, []


def get_gpu_info_pynvml() -> Optional[List[GPUInfo]]:
    """
    Get GPU information using pynvml library.

    Returns:
        List of GPUInfo objects, or None if pynvml is not available or fails
    """
    if not PYNVML_AVAILABLE:
        logger.debug("pynvml not available")
        return None

    try:
        pynvml.nvmlInit()
        gpus = []
        device_count = pynvml.nvmlDeviceGetCount()

        for i in range(device_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name_bytes = pynvml.nvmlDeviceGetName(handle)
                # Handle both bytes and string (newer nvidia-ml-py returns strings)
                name = (
                    name_bytes.decode("utf-8")
                    if isinstance(name_bytes, bytes)
                    else name_bytes
                )
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_memory = memory_info.total

                # Get driver version
                driver_version_bytes = pynvml.nvmlSystemGetDriverVersion()
                # Handle both bytes and string (newer nvidia-ml-py returns strings)
                driver_version = (
                    driver_version_bytes.decode("utf-8")
                    if isinstance(driver_version_bytes, bytes)
                    else driver_version_bytes
                )

                # CUDA version from driver (approximate)
                cuda_version = None
                try:
                    cuda_major = pynvml.nvmlSystemGetCudaDriverVersion()
                    if cuda_major:
                        cuda_version = f"{cuda_major // 1000}.{cuda_major % 1000 // 10}"
                except:
                    pass

                gpus.append(
                    GPUInfo(
                        name=name,
                        driver_version=driver_version,
                        cuda_version=cuda_version,
                        total_memory=total_memory,
                        index=i,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to get info for GPU {i}: {e}")
                continue

        pynvml.nvmlShutdown()
        return gpus

    except Exception as e:
        logger.error(f"Error initializing pynvml: {e}")
        return None


def get_gpu_info() -> Tuple[Optional[str], Optional[str], List[GPUInfo]]:
    """
    Get GPU information using the best available method.

    Tries pynvml first, falls back to nvidia-smi.

    Returns:
        Tuple of (driver_version, cuda_version, list_of_gpu_info)
    """
    # Try pynvml first (more efficient)
    if PYNVML_AVAILABLE:
        gpus = get_gpu_info_pynvml()
        if gpus:
            driver_version = gpus[0].driver_version if gpus else None
            cuda_version = gpus[0].cuda_version if gpus else None
            return driver_version, cuda_version, gpus

    # Fall back to nvidia-smi
    return get_gpu_info_nvidia_smi()


def get_gpu_metrics(index: int = 0) -> Optional[Dict]:
    """
    Get real-time GPU metrics for a specific GPU.

    Args:
        index: GPU index (default: 0)

    Returns:
        Dictionary with utilization, temperature, memory usage, power, or None if unavailable
    """
    if not PYNVML_AVAILABLE:
        # Fall back to nvidia-smi for metrics
        return get_gpu_metrics_nvidia_smi(index)

    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(index)

        # Utilization
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        utilization = util.gpu

        # Temperature
        try:
            temperature = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )
        except:
            temperature = None

        # Memory
        memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        memory_used = memory_info.used
        memory_total = memory_info.total
        memory_percent = (memory_used / memory_total) * 100 if memory_total > 0 else 0

        # Power
        try:
            power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert mW to W
        except:
            power = None

        pynvml.nvmlShutdown()

        return {
            "utilization": utilization,
            "temperature": temperature,
            "memory_used": memory_used,
            "memory_total": memory_total,
            "memory_percent": memory_percent,
            "power": power,
        }

    except Exception as e:
        logger.error(f"Error getting GPU metrics via pynvml: {e}")
        return get_gpu_metrics_nvidia_smi(index)


def get_gpu_metrics_nvidia_smi(index: int = 0) -> Optional[Dict]:
    """
    Get real-time GPU metrics using nvidia-smi.

    Args:
        index: GPU index (default: 0)

    Returns:
        Dictionary with utilization, temperature, memory usage, power, or None if unavailable
    """
    if not check_nvidia_smi():
        return None

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--id={index}",
                "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        parts = [p.strip() for p in result.stdout.strip().split(",")]
        if len(parts) >= 5:
            utilization = float(parts[0])
            temperature = float(parts[1])
            memory_used = int(parts[2]) * 1024 * 1024  # MB to bytes
            memory_total = int(parts[3]) * 1024 * 1024  # MB to bytes
            memory_percent = (
                (memory_used / memory_total) * 100 if memory_total > 0 else 0
            )
            power = float(parts[4])

            return {
                "utilization": utilization,
                "temperature": temperature,
                "memory_used": memory_used,
                "memory_total": memory_total,
                "memory_percent": memory_percent,
                "power": power,
            }

    except Exception as e:
        logger.error(f"Error getting GPU metrics via nvidia-smi: {e}")

    return None
