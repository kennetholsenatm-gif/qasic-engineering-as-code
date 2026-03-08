"""
Data Collection & Aggregation component.

Provides a simple API to create the telemetry buffer and start
collectors, decoupling callers from low-level telemetry details.
"""

from typing import Any

from telemetry.collector import (
    RollingBuffer,
    get_rolling_buffer,
    start_netflow_collector,
    start_sflow_collector,
)


def create_telemetry_buffer(window_seconds: float) -> RollingBuffer:
    """Create the shared rolling buffer for telemetry samples."""
    return get_rolling_buffer(window_seconds=window_seconds)


def start_telemetry_collectors(
    buffer: RollingBuffer,
    sflow_port: int,
    netflow_port: int,
) -> None:
    """Start sFlow and NetFlow collectors in the background."""
    start_sflow_collector(buffer, port=sflow_port)
    start_netflow_collector(buffer, port=netflow_port)


def get_buffer_handle(buffer: RollingBuffer) -> RollingBuffer:
    """Return the underlying buffer (for callers that need direct access)."""
    return buffer

