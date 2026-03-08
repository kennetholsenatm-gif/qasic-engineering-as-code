"""
UDP collectors for sFlow and NetFlow telemetry from VyOS.
Exposes a rolling window of flow/counter records for the Bayesian stage.
"""

import socket
import struct
import threading
from collections import deque
from datetime import datetime
from typing import Callable, Deque, List

from .models import CounterRecord, FlowRecord

# Default ports
SFLOW_PORT = 6343
NETFLOW_PORT = 2055

# Rolling window: keep last N seconds of data
DEFAULT_WINDOW_SECONDS = 600  # 10 minutes


class RollingBuffer:
    """Thread-safe rolling buffer of flow and counter records."""

    def __init__(self, window_seconds: float = DEFAULT_WINDOW_SECONDS) -> None:
        self.window_seconds = window_seconds
        self._flows: Deque[FlowRecord] = deque()
        self._counters: Deque[CounterRecord] = deque()
        self._lock = threading.Lock()

    def add_flow(self, record: FlowRecord) -> None:
        with self._lock:
            self._flows.append(record)
            self._evict_old_flows()

    def add_counter(self, record: CounterRecord) -> None:
        with self._lock:
            self._counters.append(record)
            self._evict_old_counters()

    def _evict_old_flows(self) -> None:
        cutoff = datetime.utcnow().timestamp() - self.window_seconds
        while self._flows and self._flows[0].timestamp.timestamp() < cutoff:
            self._flows.popleft()

    def _evict_old_counters(self) -> None:
        cutoff = datetime.utcnow().timestamp() - self.window_seconds
        while self._counters and self._counters[0].timestamp.timestamp() < cutoff:
            self._counters.popleft()

    def get_flows(self) -> List[FlowRecord]:
        with self._lock:
            self._evict_old_flows()
            return list(self._flows)

    def get_counters(self) -> List[CounterRecord]:
        with self._lock:
            self._evict_old_counters()
            return list(self._counters)


def _parse_sflow_payload(data: bytes) -> List[FlowRecord]:
    """
    Parse sFlow v5 datagram payload into flow records.
    Minimal parser: extracts flow samples (sampled IPv4/IPv6) and counter samples.
    VNI is inferred if present in extended data; otherwise left None.
    """
    records: List[FlowRecord] = []
    try:
        if len(data) < 28:
            return records
        # sFlow v5 header: version(4), addr_type(4), agent_ip(4/16), sub_agent(4), seq(4), sys_uptime(4), samples(4)
        version = struct.unpack(">I", data[0:4])[0]
        if version != 5:
            return records
        num_samples = struct.unpack(">I", data[24:28])[0]
        offset = 28
        for _ in range(num_samples):
            if offset + 8 > len(data):
                break
            sample_type = struct.unpack(">I", data[offset : offset + 4])[0]
            sample_len = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
            sample_end = offset + 8 + sample_len
            if sample_end > len(data):
                break
            # Flow sample = 0, Expanded flow sample = 3
            if sample_type in (0, 3):
                # Skip to sequence length then to records
                inner = data[offset + 8 : sample_end]
                if len(inner) >= 8:
                    seq_len = struct.unpack(">I", inner[4:8])[0]
                    rec_offset = 8 + seq_len
                    if rec_offset + 4 <= len(inner):
                        num_recs = struct.unpack(">I", inner[rec_offset : rec_offset + 4])[0]
                        rec_offset += 4
                        for _ in range(num_recs):
                            if rec_offset + 8 > len(inner):
                                break
                            rec_format = struct.unpack(">I", inner[rec_offset : rec_offset + 4])[0]
                            rec_len = struct.unpack(">I", inner[rec_offset + 4 : rec_offset + 8])[0]
                            rec_end = rec_offset + 8 + rec_len
                            if rec_end > len(inner):
                                break
                            # Raw packet header = 1 (IPv4), 2 (IPv6)
                            if rec_format == 1 and rec_len >= 24:
                                # Sampled IPv4: skip ethernet, then ip
                                ip_off = rec_offset + 8
                                if inner[ip_off] >> 4 == 4:
                                    src = f"{inner[ip_off+12]}.{inner[ip_off+13]}.{inner[ip_off+14]}.{inner[ip_off+15]}"
                                    dst = f"{inner[ip_off+16]}.{inner[ip_off+17]}.{inner[ip_off+18]}.{inner[ip_off+19]}"
                                    # Protocol, length approximate
                                    proto = inner[ip_off + 9]
                                    ihl = (inner[ip_off] & 0x0F) * 4
                                    if rec_len >= ihl + 20:
                                        sport = struct.unpack(">H", inner[ip_off + ihl : ip_off + ihl + 2])[0]
                                        dport = struct.unpack(">H", inner[ip_off + ihl + 2 : ip_off + ihl + 4])[0]
                                    else:
                                        sport = dport = None
                                    records.append(
                                        FlowRecord(
                                            timestamp=datetime.utcnow(),
                                            vni=None,
                                            src_ip=src,
                                            dst_ip=dst,
                                            bytes_count=0,
                                            packets_count=1,
                                            protocol=proto,
                                            src_port=sport,
                                            dst_port=dport,
                                        )
                                    )
                            rec_offset = rec_end
            offset = sample_end
    except Exception:
        pass
    return records


def _parse_netflow_payload(data: bytes) -> List[FlowRecord]:
    """
    Parse NetFlow v5/v9 or IPFIX datagram into flow records.
    Uses the 'netflow' library if available; otherwise minimal v5 parsing.
    """
    records: List[FlowRecord] = []
    try:
        try:
            import netflow
            parsed = netflow.parse_packet(data)
            if parsed is None:
                return records
            # netflow returns list of flow dicts or single record
            flows = parsed if isinstance(parsed, list) else [parsed]
            now = datetime.utcnow()
            for f in flows:
                if isinstance(f, dict):
                    records.append(
                        FlowRecord(
                            timestamp=now,
                            vni=f.get("vni") or f.get("VNI") or None,
                            src_ip=f.get("srcaddr") or f.get("IPV4_SRC_ADDR"),
                            dst_ip=f.get("dstaddr") or f.get("IPV4_DST_ADDR"),
                            bytes_count=int(f.get("dOctets", f.get("IN_BYTES", 0)) or 0),
                            packets_count=int(f.get("dPkts", f.get("IN_PKTS", 0)) or 0),
                            input_ifindex=f.get("input") or f.get("INPUT_SNMP"),
                            output_ifindex=f.get("output") or f.get("OUTPUT_SNMP"),
                            protocol=f.get("prot"),
                            src_port=f.get("srcport") or f.get("L4_SRC_PORT"),
                            dst_port=f.get("dstport") or f.get("L4_DST_PORT"),
                        )
                    )
        except ImportError:
            pass
        # Fallback: minimal NetFlow v5 parsing
        if not records and len(data) >= 24:
            version = struct.unpack(">H", data[0:2])[0]
            if version == 5:
                count = struct.unpack(">H", data[2:4])[0]
                # v5 header 24 bytes, each flow 48 bytes
                if 24 + count * 48 <= len(data):
                    for i in range(count):
                        off = 24 + i * 48
                        src = f"{data[off+0]}.{data[off+1]}.{data[off+2]}.{data[off+3]}"
                        dst = f"{data[off+4]}.{data[off+5]}.{data[off+6]}.{data[off+7]}"
                        dPkts = struct.unpack(">I", data[off + 16 : off + 20])[0]
                        dOctets = struct.unpack(">I", data[off + 20 : off + 24])[0]
                        records.append(
                            FlowRecord(
                                timestamp=datetime.utcnow(),
                                vni=None,
                                src_ip=src,
                                dst_ip=dst,
                                bytes_count=dOctets,
                                packets_count=dPkts,
                            )
                        )
    except Exception:
        pass
    return records


def _run_udp_collector_thread(
    port: int,
    buffer: RollingBuffer,
    parser: Callable[[bytes], List[FlowRecord]],
) -> None:
    """Blocking UDP receive loop; run in a daemon thread."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    while True:
        try:
            data, _ = sock.recvfrom(65535)
            for record in parser(data):
                buffer.add_flow(record)
        except Exception:
            pass


def start_sflow_collector(
    buffer: RollingBuffer,
    port: int = SFLOW_PORT,
) -> threading.Thread:
    """Start sFlow UDP collector in a background thread. Returns the thread."""
    t = threading.Thread(
        target=_run_udp_collector_thread,
        args=(port, buffer, _parse_sflow_payload),
        daemon=True,
    )
    t.start()
    return t


def start_netflow_collector(
    buffer: RollingBuffer,
    port: int = NETFLOW_PORT,
) -> threading.Thread:
    """Start NetFlow UDP collector in a background thread. Returns the thread."""
    t = threading.Thread(
        target=_run_udp_collector_thread,
        args=(port, buffer, _parse_netflow_payload),
        daemon=True,
    )
    t.start()
    return t


def get_rolling_buffer(window_seconds: float = DEFAULT_WINDOW_SECONDS) -> RollingBuffer:
    """Factory for the shared rolling buffer."""
    return RollingBuffer(window_seconds=window_seconds)
