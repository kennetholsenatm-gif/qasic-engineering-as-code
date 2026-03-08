# Grafana (full stack)

Grafana runs in the full Docker Compose stack (`docker-compose.full.yml`) for dashboards and visualization.

## Access

- **URL:** http://localhost:3000
- **Login:** `admin` / `admin` (override with `GRAFANA_ADMIN_PASSWORD` in `.env` or `.env.tofu`)

## InfluxDB datasource

The **InfluxDB-QASIC** datasource is configured automatically using the same token as the stack (`INFLUX_TOKEN` or default `qasic-telemetry-token`). It points at the `qasic-telemetry` bucket (Flux) for calibration/telemetry data written by `run_calibration_cycle.py` and the API.

## Dashboards

1. Log in, go to **Explore** and choose **InfluxDB-QASIC**.
2. Use **Flux** to query the `qasic-telemetry` bucket, e.g.:
   ```flux
   from(bucket: "qasic-telemetry")
     |> range(start: -24h)
     |> filter(fn: (r) => r["_measurement"] == "telemetry")
   ```
3. Create dashboards from **Dashboard** → **New** → **Add visualization**, and save.

## Provisioning

- Datasource is set via environment in `docker-compose.full.yml` (`GF_DATASOURCES_DEFAULT_*`).
- Optional: add YAML under `provisioning/dashboards` to ship default dashboards (see [Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)).

## Data persistence

Grafana storage (dashboards, users) is in the `grafana_data` volume so it survives container restarts.
