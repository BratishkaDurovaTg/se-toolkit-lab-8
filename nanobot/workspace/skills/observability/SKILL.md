---
name: observability
description: Investigate backend health with logs first, then traces
always: true
---

# Observability Skill

Use the observability MCP tools for fresh evidence about backend failures,
errors, and recent request traces.

## Tool map

- `logs_error_count` / `mcp_obs_logs_error_count`: count recent ERROR logs,
  grouped by service.
- `logs_search` / `mcp_obs_logs_search`: inspect recent structured log records
  and extract `trace_id` values when available.
- `traces_list` / `mcp_obs_traces_list`: list recent traces for a service and
  find likely failing traces.
- `traces_get` / `mcp_obs_traces_get`: inspect a specific trace and summarize
  the span hierarchy.
- `cron`: create, list, and remove chat-bound recurring health checks.

## Strategy

- When the user asks about errors, failures, or system health, start with
  `logs_error_count` on a narrow recent window.
- Prefer a scoped service when the question is about the LMS backend. The
  backend service name is `Learning Management Service`.
- If recent errors exist, call `logs_search` next to inspect the freshest
  matching records and look for `trace_id`, `event`, `path`, and `error`.
- If you find a `trace_id`, call `traces_get` for that exact trace instead of
  guessing from logs alone.
- If logs show a failing service but no `trace_id`, call `traces_list` for that
  service on the same narrow time window and inspect the freshest likely trace.
- When the user asks `What went wrong?` or `Check system health`, do the full
  investigation flow in one answer: recent error count, relevant log evidence,
  then trace evidence if available.
- For `What went wrong?`, prefer the freshest failure in the LMS backend over
  a broad historical summary.
- When the evidence shows a real backend or database failure but a user-facing
  HTTP response claims `404` or `not found`, explicitly say the failure was
  misreported by the response path.
- If no recent errors are present in the requested window, say that the system
  looks healthy instead of over-investigating older noise.
- Keep the time window fresh and narrow by default, such as 10 minutes or less,
  unless the user explicitly asks for a broader range.
- For scheduled chat health checks:
  - use `cron` instead of `HEARTBEAT.md`
  - use `every_seconds` for short interval checks such as 120 seconds
  - write the scheduled `message` so the future run knows to check recent
    backend errors, inspect a matching trace if needed, and post a short
    summary to the same chat
  - use `cron` with `action: "list"` when the user asks to list scheduled jobs
  - use `cron` with `action: "remove"` when the user asks to remove a test job

## Response style

- Summarize findings concisely. Do not dump raw JSON.
- Name the affected service and the failing operation when you can.
- Mention concrete evidence such as `severity`, `event`, `path`, `trace_id`, or
  the failing span.
- When you cite both logs and traces, make that explicit so the user can see
  why your conclusion is trustworthy.
- For proactive health reports, keep the report to a short operational summary:
  either `the system looks healthy` or a one-paragraph explanation that cites
  both log evidence and trace evidence.
