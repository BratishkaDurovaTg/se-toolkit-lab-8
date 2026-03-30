"""Stdio MCP server exposing observability tools."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from mcp_obs.observability import (
    ErrorCount,
    LogRecord,
    ObservabilityClient,
    TraceDetail,
    TraceSummary,
)
from mcp_obs.settings import resolve_settings


ToolPayload = BaseModel | list[BaseModel]


class LogsSearchQuery(BaseModel):
    keyword: str | None = Field(
        default=None,
        description="Optional keyword or phrase to search for in recent logs.",
    )
    service: str | None = Field(
        default=None,
        description="Optional OTel service.name filter, e.g. 'Learning Management Service'.",
    )
    severity: str | None = Field(
        default=None,
        description="Optional severity filter such as ERROR or INFO.",
    )
    minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Look back this many minutes from now.",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum recent matching log entries to return.",
    )


class LogsErrorCountQuery(BaseModel):
    service: str | None = Field(
        default=None,
        description="Optional OTel service.name filter. Leave empty to group all services.",
    )
    minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Look back this many minutes from now.",
    )


class TracesListQuery(BaseModel):
    service: str = Field(
        default="Learning Management Service",
        description="Service name to search in VictoriaTraces.",
    )
    minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Look back this many minutes from now.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum recent traces to return.",
    )


class TracesGetQuery(BaseModel):
    trace_id: str = Field(description="Exact trace ID to retrieve from VictoriaTraces.")


def _text(data: ToolPayload) -> list[TextContent]:
    payload: object
    if isinstance(data, BaseModel):
        payload = data.model_dump()
    else:
        payload = [item.model_dump() for item in data]
    return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]


def create_server(client: ObservabilityClient) -> Server:
    server = Server("obs")

    tool_specs: dict[str, tuple[type[BaseModel], Tool, Any]] = {
        "logs_search": (
            LogsSearchQuery,
            _tool(
                "logs_search",
                "Search recent structured logs in VictoriaLogs by keyword, service, severity, and time window. Returns recent log entries with trace IDs when available.",
                LogsSearchQuery,
            ),
            _logs_search,
        ),
        "logs_error_count": (
            LogsErrorCountQuery,
            _tool(
                "logs_error_count",
                "Count recent ERROR log entries per service in VictoriaLogs over a recent time window.",
                LogsErrorCountQuery,
            ),
            _logs_error_count,
        ),
        "traces_list": (
            TracesListQuery,
            _tool(
                "traces_list",
                "List recent traces for a service from VictoriaTraces. Use after identifying the relevant failing service in logs.",
                TracesListQuery,
            ),
            _traces_list,
        ),
        "traces_get": (
            TracesGetQuery,
            _tool(
                "traces_get",
                "Fetch a trace by ID from VictoriaTraces and summarize its span hierarchy, services, duration, and error markers.",
                TracesGetQuery,
            ),
            _traces_get,
        ),
    }

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [entry[1] for entry in tool_specs.values()]

    @server.call_tool()
    async def call_tool(
        name: str,
        arguments: dict[str, Any] | None,
    ) -> list[TextContent]:
        entry = tool_specs.get(name)
        if entry is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        model_cls, _, handler = entry
        try:
            args = model_cls.model_validate(arguments or {})
            return _text(await handler(client, args))
        except Exception as exc:
            return [
                TextContent(type="text", text=f"Error: {type(exc).__name__}: {exc}")
            ]

    _ = list_tools, call_tool
    return server


def _tool(name: str, description: str, model: type[BaseModel]) -> Tool:
    schema = model.model_json_schema()
    schema.pop("$defs", None)
    schema.pop("title", None)
    return Tool(name=name, description=description, inputSchema=schema)


async def _logs_search(client: ObservabilityClient, args: BaseModel) -> list[LogRecord]:
    query = _require_model(args, LogsSearchQuery)
    return await client.logs_search(
        keyword=query.keyword,
        service=query.service,
        severity=query.severity,
        minutes=query.minutes,
        limit=query.limit,
    )


async def _logs_error_count(
    client: ObservabilityClient, args: BaseModel
) -> list[ErrorCount]:
    query = _require_model(args, LogsErrorCountQuery)
    return await client.logs_error_count(service=query.service, minutes=query.minutes)


async def _traces_list(
    client: ObservabilityClient, args: BaseModel
) -> list[TraceSummary]:
    query = _require_model(args, TracesListQuery)
    return await client.traces_list(
        service=query.service,
        minutes=query.minutes,
        limit=query.limit,
    )


async def _traces_get(client: ObservabilityClient, args: BaseModel) -> TraceDetail:
    query = _require_model(args, TracesGetQuery)
    return await client.traces_get(trace_id=query.trace_id)


def _require_model[T: BaseModel](args: BaseModel, model: type[T]) -> T:
    if not isinstance(args, model):
        raise TypeError(f"Expected {model.__name__}, got {type(args).__name__}")
    return args


async def main(
    logs_base_url: str | None = None,
    traces_base_url: str | None = None,
) -> None:
    settings = resolve_settings(logs_base_url, traces_base_url)
    async with ObservabilityClient(
        settings.logs_base_url, settings.traces_base_url
    ) as client:
        server = create_server(client)
        async with stdio_server() as (read_stream, write_stream):
            init_options = server.create_initialization_options()
            await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
