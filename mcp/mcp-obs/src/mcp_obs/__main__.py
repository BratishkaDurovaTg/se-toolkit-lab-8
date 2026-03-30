"""CLI entrypoint for the observability MCP server."""

from __future__ import annotations

import asyncio

from mcp_obs.server import main


if __name__ == "__main__":
    asyncio.run(main())
