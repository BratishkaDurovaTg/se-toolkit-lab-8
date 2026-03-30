"""Environment-based settings for observability endpoints."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ObservabilitySettings:
    """Resolved URLs for VictoriaLogs and VictoriaTraces."""

    logs_base_url: str
    traces_base_url: str


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def resolve_settings(
    logs_base_url: str | None = None,
    traces_base_url: str | None = None,
) -> ObservabilitySettings:
    """Resolve observability base URLs from explicit values or the environment."""

    return ObservabilitySettings(
        logs_base_url=(logs_base_url or _require_env("MCP_OBS_LOGS_BASE_URL")).rstrip(
            "/"
        ),
        traces_base_url=(
            traces_base_url or _require_env("MCP_OBS_TRACES_BASE_URL")
        ).rstrip("/"),
    )
