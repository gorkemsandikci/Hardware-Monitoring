"""Hardware inventory module for detecting and cataloging system components."""

import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Check if dependencies are installed
try:
    import psutil
except ImportError:
    print("ERROR: Required dependencies are not installed.")
    print("\nPlease run the following commands:")
    print("  1. cd /home/gorkem/dev/personal/hardware-monitoring")
    print("  2. source .venv/bin/activate")
    print("  3. pip install -r requirements.txt")
    print("\nOr use the setup script:")
    print("  ./scripts/setup-venv.sh")
    sys.exit(1)

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.gpu_utils import get_gpu_info, GPUInfo
from src.utils.logger import setup_logger
from src.utils.format_utils import format_bytes

logger = setup_logger(__name__)


def get_cpu_info() -> Dict:
    """
    Get CPU information.

    Returns:
        Dictionary containing CPU model, physical cores, logical threads, and frequency
    """
    try:
        cpu_info = {
            "model": platform.processor() or "Unknown",
            "physical_cores": psutil.cpu_count(logical=False) or 0,
            "logical_threads": psutil.cpu_count(logical=True) or 0,
            "architecture": platform.machine(),
        }

        # Try to get CPU frequency
        try:
            freq = psutil.cpu_freq()
            if freq:
                cpu_info["base_frequency_mhz"] = freq.current
                cpu_info["min_frequency_mhz"] = freq.min
                cpu_info["max_frequency_mhz"] = freq.max
        except Exception as e:
            logger.debug(f"Could not get CPU frequency: {e}")

        # Try to get more detailed CPU info from /proc/cpuinfo on Linux
        if platform.system() == "Linux":
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line.lower():
                            model = line.split(":")[-1].strip()
                            if model:
                                cpu_info["model"] = model
                            break
            except Exception as e:
                logger.debug(f"Could not read /proc/cpuinfo: {e}")

        return cpu_info

    except Exception as e:
        logger.error(f"Error getting CPU info: {e}")
        return {
            "model": "Unknown",
            "physical_cores": 0,
            "logical_threads": 0,
            "architecture": "Unknown",
        }


def get_memory_info() -> Dict:
    """
    Get memory information.

    Returns:
        Dictionary containing total, available, used memory and usage percentage
    """
    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "total_bytes": memory.total,
            "available_bytes": memory.available,
            "used_bytes": memory.used,
            "usage_percent": memory.percent,
            "swap_total_bytes": swap.total,
            "swap_used_bytes": swap.used,
            "swap_percent": swap.percent,
        }

    except Exception as e:
        logger.error(f"Error getting memory info: {e}")
        return {
            "total_bytes": 0,
            "available_bytes": 0,
            "used_bytes": 0,
            "usage_percent": 0.0,
            "swap_total_bytes": 0,
            "swap_used_bytes": 0,
            "swap_percent": 0.0,
        }


def get_disk_info() -> List[Dict]:
    """
    Get disk information for all mount points.

    Returns:
        List of dictionaries containing disk information for each partition
    """
    disks = []
    try:
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "usage_percent": usage.percent,
                }
                disks.append(disk_info)
            except PermissionError:
                logger.debug(f"Permission denied accessing {partition.mountpoint}")
                continue
            except Exception as e:
                logger.warning(
                    f"Error getting disk info for {partition.mountpoint}: {e}"
                )
                continue

    except Exception as e:
        logger.error(f"Error getting disk info: {e}")

    return disks


def get_network_info() -> List[Dict]:
    """
    Get network interface information.

    Returns:
        List of dictionaries containing network interface information
    """
    interfaces = []
    try:
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()

        for interface_name, addresses in net_if_addrs.items():
            # Skip loopback
            if interface_name == "lo":
                continue

            interface_info = {
                "name": interface_name,
                "addresses": [],
                "is_up": False,
                "speed_mbps": None,
            }

            # Get addresses
            for addr in addresses:
                addr_info = {
                    "family": str(addr.family),
                    "address": addr.address,
                }
                if addr.netmask:
                    addr_info["netmask"] = addr.netmask
                if addr.broadcast:
                    addr_info["broadcast"] = addr.broadcast
                interface_info["addresses"].append(addr_info)

            # Get interface stats
            if interface_name in net_if_stats:
                stats = net_if_stats[interface_name]
                interface_info["is_up"] = stats.isup
                interface_info["speed_mbps"] = stats.speed

            interfaces.append(interface_info)

    except Exception as e:
        logger.error(f"Error getting network info: {e}")

    return interfaces


def get_gpu_info_dict() -> Dict:
    """
    Get GPU information as dictionary.

    Returns:
        Dictionary containing driver version, CUDA version, and list of GPUs
    """
    try:
        driver_version, cuda_version, gpus = get_gpu_info()

        gpu_list = []
        for gpu in gpus:
            gpu_dict = {
                "index": gpu.index,
                "name": gpu.name,
                "driver_version": gpu.driver_version,
                "cuda_version": gpu.cuda_version,
                "total_memory_bytes": gpu.total_memory,
            }
            gpu_list.append(gpu_dict)

        return {
            "driver_version": driver_version,
            "cuda_version": cuda_version,
            "gpus": gpu_list,
            "gpu_count": len(gpu_list),
        }

    except Exception as e:
        logger.error(f"Error getting GPU info: {e}")
        return {
            "driver_version": None,
            "cuda_version": None,
            "gpus": [],
            "gpu_count": 0,
        }


def get_system_info() -> Dict:
    """
    Get general system information.

    Returns:
        Dictionary containing OS, hostname, and platform information
    """
    try:
        return {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "platform": platform.platform(),
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {
            "hostname": "Unknown",
            "os": "Unknown",
            "os_version": "Unknown",
            "os_release": "Unknown",
            "platform": "Unknown",
        }


def collect_inventory() -> Dict:
    """
    Collect complete hardware inventory.

    Returns:
        Dictionary containing all hardware information with timestamp
    """
    logger.info("Collecting hardware inventory...")

    inventory = {
        "timestamp": datetime.now().isoformat(),
        "system": get_system_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disks": get_disk_info(),
        "network": get_network_info(),
        "gpu": get_gpu_info_dict(),
    }

    logger.info("Hardware inventory collected successfully")
    return inventory


def save_inventory(inventory: Dict, output_file: Path) -> None:
    """
    Save inventory to JSON file.

    Args:
        inventory: Inventory dictionary
        output_file: Path to output JSON file
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)
        logger.info(f"Inventory saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving inventory to {output_file}: {e}")
        raise


def print_inventory_summary(inventory: Dict) -> None:
    """
    Print a human-readable summary of the inventory.

    Args:
        inventory: Inventory dictionary
    """
    print("\n" + "=" * 60)
    print("HARDWARE INVENTORY SUMMARY")
    print("=" * 60)
    print(f"Timestamp: {inventory['timestamp']}")
    print(f"Hostname: {inventory['system']['hostname']}")
    print(f"OS: {inventory['system']['os']} {inventory['system']['os_release']}")

    print("\n--- CPU ---")
    cpu = inventory["cpu"]
    print(f"Model: {cpu['model']}")
    print(f"Physical Cores: {cpu['physical_cores']}")
    print(f"Logical Threads: {cpu['logical_threads']}")

    print("\n--- Memory ---")
    mem = inventory["memory"]
    print(f"Total: {format_bytes(mem['total_bytes'])}")
    print(f"Available: {format_bytes(mem['available_bytes'])}")
    print(f"Used: {format_bytes(mem['used_bytes'])} ({mem['usage_percent']:.1f}%)")

    print("\n--- Disks ---")
    for disk in inventory["disks"]:
        print(
            f"{disk['device']} ({disk['mountpoint']}): "
            f"{format_bytes(disk['used_bytes'])} / {format_bytes(disk['total_bytes'])} "
            f"({disk['usage_percent']:.1f}%)"
        )

    print("\n--- Network Interfaces ---")
    for iface in inventory["network"]:
        status = "UP" if iface["is_up"] else "DOWN"
        print(f"{iface['name']}: {status}")
        for addr in iface["addresses"]:
            if "address" in addr:
                print(f"  {addr['family']}: {addr['address']}")

    print("\n--- GPU ---")
    gpu_info = inventory["gpu"]
    if gpu_info["gpu_count"] > 0:
        print(f"Driver Version: {gpu_info['driver_version']}")
        print(f"CUDA Version: {gpu_info['cuda_version'] or 'Unknown'}")
        print(f"GPU Count: {gpu_info['gpu_count']}")
        for gpu in gpu_info["gpus"]:
            print(
                f"  GPU {gpu['index']}: {gpu['name']} "
                f"({format_bytes(gpu['total_memory_bytes'])})"
            )
    else:
        print("No NVIDIA GPUs detected")

    print("=" * 60 + "\n")


def main() -> None:
    """Main entry point for inventory script."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect hardware inventory")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSON file path (default: inventory_<timestamp>.json)",
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Don't print summary to console",
    )

    args = parser.parse_args()

    # Collect inventory
    inventory = collect_inventory()

    # Print summary
    if not args.no_print:
        print_inventory_summary(inventory)

    # Save to file
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(f"inventory_{timestamp}.json")

    save_inventory(inventory, output_file)
    print(f"Inventory saved to: {output_file}")


if __name__ == "__main__":
    main()
