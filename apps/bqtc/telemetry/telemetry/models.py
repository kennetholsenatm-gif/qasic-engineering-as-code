"""Dataclasses for flow and counter records from sFlow/NetFlow telemetry."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FlowRecord:
    """A single flow sample (sampled packet or flow export record)."""

    timestamp: datetime
    vni: Optional[int] = None  # EVPN VNI; None if not VXLAN/EVPN
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    bytes_count: int = 0
    packets_count: int = 0
    input_ifindex: Optional[int] = None
    output_ifindex: Optional[int] = None
    protocol: Optional[int] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.timestamp, (int, float)):
            self.timestamp = datetime.utcfromtimestamp(float(self.timestamp))


@dataclass
class CounterRecord:
    """Interface or host counter sample."""

    timestamp: datetime
    ifindex: int
    bytes_in: int = 0
    bytes_out: int = 0
    packets_in: int = 0
    packets_out: int = 0
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.timestamp, (int, float)):
            self.timestamp = datetime.utcfromtimestamp(float(self.timestamp))
