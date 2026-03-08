"""
Load YAML config into pydantic models. Env overrides for app paths and CORS.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

CONFIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = CONFIG_DIR.parent


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        content = f.read()
    try:
        import yaml
        return yaml.safe_load(content) or {}
    except ImportError:
        import json
        # fallback: YAML is often JSON-like for simple keys
        return {}


# --- Pydantic models ---


class AppPathsConfig(BaseModel):
    pipeline_base: str = "pipeline_result"
    engineering_dir: str = "engineering"
    docs_dir: str = "docs"
    # Credentials vault file (in container or host path). Env: QASIC_CREDENTIALS_FILE.
    credentials_file: str = ""
    # Artifact store base path for file:// backend. Env: QASIC_ARTIFACT_STORE_BASE.
    artifact_store_base: str = ""


class CorsConfig(BaseModel):
    allow_origins: str = ""  # Production: set BACKEND_CORS_ORIGINS to a whitelist
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])


class AppConfig(BaseModel):
    title: str = "QASIC Engineering-as-Code API"
    version: str = "0.1.0"
    paths: AppPathsConfig = Field(default_factory=AppPathsConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)

    @classmethod
    def from_yaml(cls, repo_root: Path | None = None) -> "AppConfig":
        data = _load_yaml("app_config.yaml")
        app = data.get("app", {})
        paths = data.get("paths", {})
        cors = data.get("cors", {})
        repo_root = repo_root or REPO_ROOT
        if os.environ.get("QASIC_PIPELINE_BASE"):
            paths["pipeline_base"] = os.environ["QASIC_PIPELINE_BASE"]
        if os.environ.get("QASIC_CREDENTIALS_FILE"):
            paths["credentials_file"] = os.environ["QASIC_CREDENTIALS_FILE"]
        if os.environ.get("QASIC_ARTIFACT_STORE_BASE"):
            paths["artifact_store_base"] = os.environ["QASIC_ARTIFACT_STORE_BASE"]
        if os.environ.get("BACKEND_CORS_ORIGINS"):
            cors["allow_origins"] = os.environ["BACKEND_CORS_ORIGINS"]
        return cls(
            title=app.get("title", "QASIC Engineering-as-Code API"),
            version=app.get("version", "0.1.0"),
            paths=AppPathsConfig(**paths),
            cors=CorsConfig(**cors),
        )


class ThermalConfig(BaseModel):
    nw_per_cell_limit: float = 18.0
    t_10mk_limit_k: float = 0.015
    t_4k_limit_k: float = 5.0
    t_50k_limit_k: float = 55.0
    r_10mk: float = 1.0e-6
    r_4k: float = 1.0e-7
    r_50k: float = 1.0e-8
    t_base_10mk_k: float = 0.01
    t_base_4k_k: float = 4.0
    t_base_50k_k: float = 50.0
    power_cap_factor: float = 2.0
    phase_dev_scale: float = 0.14

    @classmethod
    def from_yaml(cls) -> "ThermalConfig":
        data = _load_yaml("thermal_config.yaml")
        thermal = data.get("thermal", {})
        return cls(**{k: v for k, v in thermal.items() if k in cls.model_fields})


class PipelineConfig(BaseModel):
    output_base: str = "pipeline_result"
    device: str = "auto"
    model: str = "mlp"
    routing_method: str = "qaoa"
    heac_library_path: str | None = None
    pdk_config_path: str | None = None

    @classmethod
    def from_yaml(cls) -> "PipelineConfig":
        data = _load_yaml("pipeline_config.yaml")
        pipeline = data.get("pipeline", {})
        return cls(**{k: v for k, v in pipeline.items() if k in cls.model_fields})


class ArtifactStoreConfig(BaseModel):
    type: str = "mlflow"
    tracking_uri: str | None = None
    experiment_name: str = "qasic-engineering"


class InfluxConfig(BaseModel):
    url: str | None = None
    token: str | None = None
    org: str | None = None
    bucket: str = "qasic-telemetry"


class DatabaseConfig(BaseModel):
    url: str | None = None


class StorageConfig(BaseModel):
    artifact_store: ArtifactStoreConfig = Field(default_factory=ArtifactStoreConfig)
    influx: InfluxConfig = Field(default_factory=InfluxConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    @classmethod
    def from_yaml(cls) -> "StorageConfig":
        data = _load_yaml("storage_config.yaml")
        artifact = data.get("artifact_store", {})
        influx = data.get("influx", {})
        database = data.get("database", {})
        if os.environ.get("MLFLOW_TRACKING_URI"):
            artifact["tracking_uri"] = os.environ["MLFLOW_TRACKING_URI"]
        if os.environ.get("INFLUX_URL"):
            influx["url"] = os.environ["INFLUX_URL"]
        if os.environ.get("INFLUX_TOKEN"):
            influx["token"] = os.environ["INFLUX_TOKEN"]
        if os.environ.get("INFLUX_ORG"):
            influx["org"] = os.environ["INFLUX_ORG"]
        if os.environ.get("INFLUX_BUCKET"):
            influx["bucket"] = os.environ["INFLUX_BUCKET"]
        if os.environ.get("DATABASE_URL"):
            database["url"] = os.environ["DATABASE_URL"]
        return cls(
            artifact_store=ArtifactStoreConfig(**artifact),
            influx=InfluxConfig(**influx),
            database=DatabaseConfig(**database),
        )


# --- Singletons (lazy) ---

_app_config: AppConfig | None = None
_thermal_config: ThermalConfig | None = None
_pipeline_config: PipelineConfig | None = None
_storage_config: StorageConfig | None = None


def load_app_config(repo_root: Path | None = None) -> AppConfig:
    global _app_config
    if _app_config is None:
        _app_config = AppConfig.from_yaml(repo_root=repo_root)
    return _app_config


def load_thermal_config() -> ThermalConfig:
    global _thermal_config
    if _thermal_config is None:
        _thermal_config = ThermalConfig.from_yaml()
    return _thermal_config


def load_pipeline_config() -> PipelineConfig:
    global _pipeline_config
    if _pipeline_config is None:
        _pipeline_config = PipelineConfig.from_yaml()
    return _pipeline_config


def get_app_config() -> AppConfig:
    return load_app_config()


def get_thermal_config() -> ThermalConfig:
    return load_thermal_config()


def get_pipeline_config() -> PipelineConfig:
    return load_pipeline_config()


def load_storage_config() -> StorageConfig:
    global _storage_config
    if _storage_config is None:
        _storage_config = StorageConfig.from_yaml()
    return _storage_config


def get_storage_config() -> StorageConfig:
    return load_storage_config()
