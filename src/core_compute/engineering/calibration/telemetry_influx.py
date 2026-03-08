"""
Optional InfluxDB writer/reader for quantum telemetry (T1/T2, gate fidelities).
Set INFLUX_URL (and INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET) to enable.
Schema aligns with telemetry_schema.py: timestamp, qubits[], gate_fidelities[], aggregate.
"""
from __future__ import annotations

import os
from typing import Any


def _client():
    try:
        from influxdb_client import InfluxDBClient
    except ImportError:
        return None
    url = os.environ.get("INFLUX_URL", "").strip()
    if not url:
        try:
            from config import get_storage_config
            url = get_storage_config().influx.url or ""
        except Exception:
            pass
    if not url:
        return None
    token = os.environ.get("INFLUX_TOKEN", "").strip()
    if not token:
        try:
            from config import get_storage_config
            token = get_storage_config().influx.token or ""
        except Exception:
            pass
    org = os.environ.get("INFLUX_ORG", "").strip()
    if not org:
        try:
            from config import get_storage_config
            org = get_storage_config().influx.org or ""
        except Exception:
            pass
    return InfluxDBClient(url=url, token=token or "", org=org)


def _bucket() -> str:
    try:
        from config import get_storage_config
        return get_storage_config().influx.bucket or "qasic-telemetry"
    except Exception:
        return os.environ.get("INFLUX_BUCKET", "qasic-telemetry")


def is_enabled() -> bool:
    c = _client()
    if c is None:
        return False
    try:
        c.ping()
        return True
    except Exception:
        return False


def _telemetry_to_point(ts_iso: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build a single point: measurement=telemetry, tag=qubit index, fields T1_us, T2_us, etc."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        ts = dt.timestamp()
    except Exception:
        import time
        ts = time.time()
    fields = {}
    if "aggregate" in data and isinstance(data["aggregate"], dict):
        for k, v in data["aggregate"].items():
            if isinstance(v, (int, float)):
                fields[f"agg_{k}"] = v
    for i, q in enumerate(data.get("qubits") or []):
        if not isinstance(q, dict):
            continue
        for key in ("T1_us", "T2_us", "phase_offset_rad"):
            if key in q and isinstance(q[key], (int, float)):
                fields[f"q{i}_{key}"] = q[key]
    for i, g in enumerate(data.get("gate_fidelities") or [])[:20]:
        if isinstance(g, dict) and "fidelity" in g and isinstance(g["fidelity"], (int, float)):
            fields[f"gate_fidelity_{i}"] = g["fidelity"]
    return {"timestamp": int(ts * 1e9), "fields": fields, "tags": {}}


def write_telemetry(telemetry: dict[str, Any] | list[dict[str, Any]]) -> bool:
    """
    Write one or more telemetry snapshots to InfluxDB.
    Each dict should have timestamp_iso and qubits (and optionally gate_fidelities, aggregate).
    Returns True if written, False if Influx not configured or on error.
    """
    client = _client()
    if client is None:
        return False
    if isinstance(telemetry, dict):
        telemetry = [telemetry]
    try:
        from influxdb_client import Point
        write_api = client.write_api()
        bucket = _bucket()
        for data in telemetry:
            ts_iso = data.get("timestamp_iso") or ""
            if not ts_iso:
                import time
                from datetime import datetime, timezone
                ts_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            pt = _telemetry_to_point(ts_iso, data)
            point = Point("telemetry").time(pt["timestamp"])
            for k, v in pt["fields"].items():
                point = point.field(k, v)
            write_api.write(bucket=bucket, record=point)
        return True
    except Exception:
        return False
    finally:
        try:
            client.close()
        except Exception:
            pass


def query_telemetry(start_iso: str | None = None, stop_iso: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    """
    Query telemetry from InfluxDB in the given time range.
    Returns list of dicts with timestamp_iso and field values (caller can reshape to telemetry_schema).
    """
    client = _client()
    if client is None:
        return []
    try:
        query_api = client.query_api()
        bucket = _bucket()
        if start_iso and stop_iso:
            range_part = f'range(start: time(v: "{start_iso}"), stop: time(v: "{stop_iso}"))'
        else:
            range_part = f'range(start: -30d)'
        q = f'from(bucket:"{bucket}") |> {range_part} |> filter(fn: (r) => r["_measurement"] == "telemetry") |> limit(n: {limit})'
        tables = query_api.query(q)
        out = []
        for table in tables:
            for row in table.records:
                rec = {"timestamp_iso": row.get_time().isoformat() + "Z", "fields": {}}
                for k, v in (row.values or {}).items():
                    if k.startswith("_") or k in ("result", "table"):
                        continue
                    rec["fields"][k] = v
                out.append(rec)
        return out
    except Exception:
        return []
    finally:
        try:
            client.close()
        except Exception:
            pass
