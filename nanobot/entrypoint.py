from __future__ import annotations

import json
import os
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
RESOLVED_CONFIG_PATH = APP_DIR / "config.resolved.json"
WORKSPACE_PATH = APP_DIR / "workspace"
NANOBOT_BIN = APP_DIR / ".venv" / "bin" / "nanobot"


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())

    defaults = config.setdefault("agents", {}).setdefault("defaults", {})
    defaults["provider"] = "custom"
    defaults["model"] = require_env("LLM_API_MODEL")
    defaults["workspace"] = str(WORKSPACE_PATH)

    custom_provider = config.setdefault("providers", {}).setdefault("custom", {})
    custom_provider["apiKey"] = require_env("LLM_API_KEY")
    custom_provider["apiBase"] = require_env("LLM_API_BASE_URL")

    gateway = config.setdefault("gateway", {})
    gateway["host"] = require_env("NANOBOT_GATEWAY_CONTAINER_ADDRESS")
    gateway["port"] = int(require_env("NANOBOT_GATEWAY_CONTAINER_PORT"))

    access_key = require_env("NANOBOT_ACCESS_KEY")

    channels = config.setdefault("channels", {})
    webchat = channels.setdefault("webchat", {})
    webchat["enabled"] = True
    webchat["host"] = require_env("NANOBOT_WEBCHAT_CONTAINER_ADDRESS")
    webchat["port"] = int(require_env("NANOBOT_WEBCHAT_CONTAINER_PORT"))
    webchat["allowFrom"] = ["*"]

    ui_relay_host = os.environ.get("NANOBOT_UI_RELAY_HOST", "127.0.0.1")
    ui_relay_port = int(os.environ.get("NANOBOT_UI_RELAY_PORT", "8766"))
    ui_relay_token = os.environ.get("NANOBOT_UI_RELAY_TOKEN", access_key)

    os.environ["NANOBOT_UI_RELAY_HOST"] = ui_relay_host
    os.environ["NANOBOT_UI_RELAY_PORT"] = str(ui_relay_port)
    os.environ["NANOBOT_UI_RELAY_TOKEN"] = ui_relay_token

    tools = config.setdefault("tools", {})
    mcp_servers = tools.setdefault("mcpServers", {})

    lms_server = mcp_servers.setdefault("lms", {})
    lms_server["command"] = "python"
    lms_server["args"] = ["-m", "mcp_lms"]
    lms_server["env"] = {
        "NANOBOT_LMS_BACKEND_URL": require_env("NANOBOT_LMS_BACKEND_URL"),
        "NANOBOT_LMS_API_KEY": require_env("NANOBOT_LMS_API_KEY"),
    }

    webchat_server = mcp_servers.setdefault("webchat", {})
    webchat_server["command"] = "python"
    webchat_server["args"] = ["-m", "mcp_webchat"]
    webchat_server["env"] = {
        "NANOBOT_UI_RELAY_URL": f"http://{ui_relay_host}:{ui_relay_port}",
        "NANOBOT_UI_RELAY_TOKEN": ui_relay_token,
    }

    obs_server = mcp_servers.setdefault("obs", {})
    obs_server["command"] = "python"
    obs_server["args"] = ["-m", "mcp_obs"]
    obs_server["env"] = {
        "MCP_OBS_LOGS_BASE_URL": require_env("NANOBOT_OBS_LOGS_BASE_URL"),
        "MCP_OBS_TRACES_BASE_URL": require_env("NANOBOT_OBS_TRACES_BASE_URL"),
    }

    RESOLVED_CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")

    os.execvp(
        str(NANOBOT_BIN),
        [
            str(NANOBOT_BIN),
            "gateway",
            "--config",
            str(RESOLVED_CONFIG_PATH),
            "--workspace",
            str(WORKSPACE_PATH),
        ],
    )


if __name__ == "__main__":
    main()
