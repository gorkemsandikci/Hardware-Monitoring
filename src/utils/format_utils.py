"""Formatting utilities for hardware monitoring."""

from typing import Union


def format_bytes(bytes_value: Union[int, float]) -> str:
    """
    Convert bytes to human-readable format.

    Args:
        bytes_value: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format percentage value.

    Args:
        value: Percentage value (0-100)
        decimals: Number of decimal places

    Returns:
        Formatted string (e.g., "45.5%")
    """
    return f"{value:.{decimals}f}%"


def format_temperature(celsius: float) -> str:
    """
    Format temperature in Celsius.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Formatted string (e.g., "45.5°C")
    """
    return f"{celsius:.1f}°C"


def format_frequency(hz: float) -> str:
    """
    Format frequency in Hz to GHz.

    Args:
        hz: Frequency in Hz

    Returns:
        Formatted string (e.g., "3.5 GHz")
    """
    if hz >= 1e9:
        return f"{hz / 1e9:.2f} GHz"
    elif hz >= 1e6:
        return f"{hz / 1e6:.2f} MHz"
    elif hz >= 1e3:
        return f"{hz / 1e3:.2f} kHz"
    return f"{hz:.2f} Hz"
