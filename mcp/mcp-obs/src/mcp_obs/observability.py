"""Typed observability client for VictoriaLogs and VictoriaTraces."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
import json
from typing import Any, cast

import httpx
from pydantic import BaseModel, Field


class LogRecord(BaseModel):
    """Selected structured fields from a VictoriaLogs entry."""

    timestamp: str | None = Field(default=None)
    service_name: str | None = Field(default=None)
    severity: str | None = Field(default=None)
    event: str | None = Field(default=None)
    message: str | None = Field(default=None)
    trace_id: str | None = Field(default=None)
    path: str | None = Field(default=None)
    method: str | None = Field(default=None)
    status: int | None = Field(default=None)
    operation: str | None = Field(default=None)
    table: str | None = Field(default=None)
    error: str | None = Field(default=None)


class ErrorCount(BaseModel):
    """Error log count for a single service over a recent window."""

    service_name: str = Field(description="OTel service.name value.")
    error_count: int = Field(ge=0, description="Number of matching error logs.")
    window_minutes: int = Field(ge=1, description="Lookback window in minutes.")


class TraceSummary(BaseModel):
    """High-level summary for a recent trace."""

    trace_id: str = Field(description="Jaeger/VictoriaTraces trace ID.")
    root_service: str | None = Field(default=None)
    root_operation: str | None = Field(default=None)
    start_time: str | None = Field(default=None)
    duration_ms: float = Field(ge=0, description="End-to-end trace duration.")
    span_count: int = Field(ge=0)
    error_span_count: int = Field(ge=0)


class TraceSpan(BaseModel):
    """Flattened trace span with derived hierarchy depth."""

    span_id: str = Field(description="Span ID.")
    parent_span_id: str | None = Field(default=None)
    depth: int = Field(ge=0, description="Approximate depth in the span tree.")
    service_name: str | None = Field(default=None)
    operation: str | None = Field(default=None)
    start_time: str | None = Field(default=None)
    duration_ms: float = Field(ge=0)
    status: str | None = Field(default=None)
    error: str | None = Field(default=None)


class TraceDetail(BaseModel):
    """Condensed trace detail for agent reasoning."""

    trace_id: str = Field(description="Jaeger/VictoriaTraces trace ID.")
    root_service: str | None = Field(default=None)
    root_operation: str | None = Field(default=None)
    start_time: str | None = Field(default=None)
    duration_ms: float = Field(ge=0)
    span_count: int = Field(ge=0)
    error_span_count: int = Field(ge=0)
    services: list[str] = Field(default_factory=lambda: cast(list[str], []))
    spans: list[TraceSpan] = Field(default_factory=lambda: cast(list[TraceSpan], []))


class ObservabilityClient:
    """Async client for VictoriaLogs and VictoriaTraces HTTP APIs."""

    def __init__(
        self,
        logs_base_url: str,
        traces_base_url: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.logs_base_url = logs_base_url.rstrip("/")
        self.traces_base_url = traces_base_url.rstrip("/")
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> ObservabilityClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()

    async def logs_search(
        self,
        *,
        keyword: str | None,
        service: str | None,
        severity: str | None,
        minutes: int,
        limit: int,
    ) -> list[LogRecord]:
        query = _build_logs_query(
            keyword=keyword,
            service=service,
            severity=severity,
            minutes=minutes,
        )
        response = await self._http_client.post(
            f"{self.logs_base_url}/select/logsql/query",
            data={"query": query, "limit": str(limit)},
        )
        response.raise_for_status()
        records: list[LogRecord] = []
        for line in response.text.splitlines():
            if not line.strip():
                continue
            payload = _mapping_or_none(json.loads(line))
            if payload is None:
                continue
            records.append(_coerce_log_record(payload))
        return records

    async def logs_error_count(
        self,
        *,
        service: str | None,
        minutes: int,
    ) -> list[ErrorCount]:
        query = _build_logs_query(
            keyword=None,
            service=service,
            severity="ERROR",
            minutes=minutes,
        )
        stats_query = f"{query} | stats by (service.name) count() error_count"
        response = await self._http_client.post(
            f"{self.logs_base_url}/select/logsql/stats_query",
            data={"query": stats_query, "time": "now"},
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("data", {}).get("result", [])
        counts: list[ErrorCount] = []
        for item in results:
            metric = item.get("metric", {})
            value = item.get("value", [0, "0"])
            counts.append(
                ErrorCount(
                    service_name=str(metric.get("service.name", "unknown")),
                    error_count=int(value[1]),
                    window_minutes=minutes,
                )
            )
        if counts or service is not None:
            return counts

        fallback_counts = Counter(
            record.service_name or "unknown"
            for record in await self.logs_search(
                keyword=None,
                service=None,
                severity="ERROR",
                minutes=minutes,
                limit=200,
            )
        )
        return [
            ErrorCount(
                service_name=service_name,
                error_count=error_count,
                window_minutes=minutes,
            )
            for service_name, error_count in sorted(fallback_counts.items())
        ]

    async def traces_list(
        self,
        *,
        service: str,
        minutes: int,
        limit: int,
    ) -> list[TraceSummary]:
        end = datetime.now(tz=UTC)
        start = end - timedelta(minutes=minutes)
        response = await self._http_client.get(
            f"{self.traces_base_url}/select/jaeger/api/traces",
            params={
                "service": service,
                "limit": str(limit),
                "start": str(_to_unix_micros(start)),
                "end": str(_to_unix_micros(end)),
            },
        )
        response.raise_for_status()
        payload = _mapping_or_none(response.json()) or {}
        traces = _list_of_mappings(payload.get("data"))
        return [_build_trace_summary(trace) for trace in traces]

    async def traces_get(self, *, trace_id: str) -> TraceDetail:
        response = await self._http_client.get(
            f"{self.traces_base_url}/select/jaeger/api/traces/{trace_id}"
        )
        response.raise_for_status()
        payload = _mapping_or_none(response.json()) or {}
        trace = payload.get("data")
        trace_payload = _mapping_or_none(trace)
        if trace_payload is None:
            traces = _list_of_mappings(trace)
            if not traces:
                raise RuntimeError(f"Unexpected trace payload for {trace_id}")
            trace_payload = traces[0]
        return _build_trace_detail(trace_payload)


def _build_logs_query(
    *,
    keyword: str | None,
    service: str | None,
    severity: str | None,
    minutes: int,
) -> str:
    terms = [f"_time:{minutes}m"]
    if service:
        terms.append(_field_filter("service.name", service))
    if severity:
        terms.append(_field_filter("severity", severity.upper()))
    if keyword:
        terms.append(_quote(keyword))
    return " AND ".join(terms)


def _field_filter(field: str, value: str) -> str:
    return f"{field}:{_quote(value)}"


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _coerce_log_record(payload: dict[str, Any]) -> LogRecord:
    status_value = payload.get("status")
    status = (
        int(status_value)
        if isinstance(status_value, int | str) and str(status_value).isdigit()
        else None
    )
    return LogRecord(
        timestamp=_string_or_none(payload.get("_time")),
        service_name=_string_or_none(payload.get("service.name")),
        severity=_string_or_none(payload.get("severity")),
        event=_string_or_none(payload.get("event")),
        message=_string_or_none(payload.get("_msg")),
        trace_id=_string_or_none(payload.get("trace_id")),
        path=_string_or_none(payload.get("path")),
        method=_string_or_none(payload.get("method")),
        status=status,
        operation=_string_or_none(payload.get("operation")),
        table=_string_or_none(payload.get("table")),
        error=_string_or_none(payload.get("error")),
    )


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _mapping_or_none(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    mapping = cast(dict[object, object], value)
    return {str(key): item for key, item in mapping.items()}


def _list_of_mappings(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = cast(list[object], value)
    mappings: list[dict[str, Any]] = []
    for item in items:
        payload = _mapping_or_none(item)
        if payload is not None:
            mappings.append(payload)
    return mappings


def _to_unix_micros(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000)


def _build_trace_summary(trace: dict[str, Any]) -> TraceSummary:
    spans = _sorted_spans(trace)
    root_span = _root_span(spans)
    service_by_process = _service_by_process(trace)
    trace_id = _string_or_none(trace.get("traceID")) or "unknown"
    return TraceSummary(
        trace_id=trace_id,
        root_service=_span_service_name(root_span, service_by_process),
        root_operation=_string_or_none(root_span.get("operationName")),
        start_time=_micros_to_iso(root_span.get("startTime")),
        duration_ms=_trace_duration_ms(spans),
        span_count=len(spans),
        error_span_count=sum(1 for span in spans if _span_error(span)),
    )


def _build_trace_detail(trace: dict[str, Any]) -> TraceDetail:
    spans = _sorted_spans(trace)
    service_by_process = _service_by_process(trace)
    root_span = _root_span(spans)
    spans_by_id = {str(span.get("spanID")): span for span in spans}
    detail_spans = [
        TraceSpan(
            span_id=str(span.get("spanID", "")),
            parent_span_id=_parent_span_id(span),
            depth=_span_depth(span, spans_by_id),
            service_name=_span_service_name(span, service_by_process),
            operation=_string_or_none(span.get("operationName")),
            start_time=_micros_to_iso(span.get("startTime")),
            duration_ms=round(float(span.get("duration", 0)) / 1000, 3),
            status=_span_status(span),
            error=_span_error(span),
        )
        for span in spans
    ]
    services = sorted(
        {
            service_name
            for service_name in (
                _span_service_name(span, service_by_process) for span in spans
            )
            if service_name
        }
    )
    return TraceDetail(
        trace_id=_string_or_none(trace.get("traceID")) or "unknown",
        root_service=_span_service_name(root_span, service_by_process),
        root_operation=_string_or_none(root_span.get("operationName")),
        start_time=_micros_to_iso(root_span.get("startTime")),
        duration_ms=_trace_duration_ms(spans),
        span_count=len(spans),
        error_span_count=sum(1 for span in spans if _span_error(span)),
        services=services,
        spans=detail_spans,
    )


def _sorted_spans(trace: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        _list_of_mappings(trace.get("spans")),
        key=lambda span: int(span.get("startTime", 0)),
    )


def _root_span(spans: list[dict[str, Any]]) -> dict[str, Any]:
    for span in spans:
        if _parent_span_id(span) is None:
            return span
    return spans[0] if spans else {}


def _service_by_process(trace: dict[str, Any]) -> dict[str, str]:
    raw_processes = _mapping_or_none(trace.get("processes"))
    if raw_processes is None:
        return {}
    service_by_process: dict[str, str] = {}
    for process_id, process_value in raw_processes.items():
        process = _mapping_or_none(process_value)
        if process is None:
            continue
        service_name = _string_or_none(process.get("serviceName"))
        if service_name is not None:
            service_by_process[process_id] = service_name
    return service_by_process


def _span_service_name(
    span: dict[str, Any], service_by_process: dict[str, str]
) -> str | None:
    process_id = _string_or_none(span.get("processID"))
    if process_id is None:
        return None
    return service_by_process.get(process_id)


def _parent_span_id(span: dict[str, Any]) -> str | None:
    references = _list_of_mappings(span.get("references"))
    for reference in references:
        if reference.get("refType") == "CHILD_OF":
            return _string_or_none(reference.get("spanID"))
    for reference in references:
        return _string_or_none(reference.get("spanID"))
    return None


def _span_depth(span: dict[str, Any], spans_by_id: dict[str, dict[str, Any]]) -> int:
    depth = 0
    seen: set[str] = set()
    parent_id = _parent_span_id(span)
    while parent_id:
        if parent_id in seen:
            break
        seen.add(parent_id)
        parent = spans_by_id.get(parent_id)
        if parent is None:
            break
        depth += 1
        parent_id = _parent_span_id(parent)
    return depth


def _span_status(span: dict[str, Any]) -> str | None:
    for tag in _list_of_mappings(span.get("tags")):
        key = _string_or_none(tag.get("key"))
        if key == "otel.status_code":
            return _string_or_none(tag.get("value"))
    return None


def _span_error(span: dict[str, Any]) -> str | None:
    messages: list[str] = []
    status = _span_status(span)
    if status and status.upper() == "ERROR":
        messages.append(status)
    for tag in _list_of_mappings(span.get("tags")):
        key = _string_or_none(tag.get("key"))
        value = _string_or_none(tag.get("value"))
        if key is None or value is None:
            continue
        if key == "error" and value.lower() not in {"false", "0"}:
            messages.append(value)
        if key in {"error.message", "exception.message"}:
            messages.append(value)
    if not messages:
        return None
    return "; ".join(dict.fromkeys(messages))


def _trace_duration_ms(spans: list[dict[str, Any]]) -> float:
    if not spans:
        return 0.0
    start = min(int(span.get("startTime", 0)) for span in spans)
    end = max(
        int(span.get("startTime", 0)) + int(span.get("duration", 0)) for span in spans
    )
    return round((end - start) / 1000, 3)


def _micros_to_iso(value: object) -> str | None:
    if not isinstance(value, int | float | str):
        return None
    try:
        micros = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(micros / 1_000_000, tz=UTC).isoformat()
