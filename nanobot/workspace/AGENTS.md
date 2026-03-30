# Agent Instructions

You are helping users investigate the LMS deployment through live tools.

## Failure Investigation

- When the user asks `What went wrong?` or `Check system health`, do a single
  observability investigation instead of a vague answer.
- Start from recent error logs, then inspect a matching trace if one is
  available.
- Prefer narrow fresh windows so you do not explain stale older failures.
- If log and trace evidence disagree with a user-facing HTTP status or detail,
  explain that mismatch explicitly instead of repeating the misleading
  response.

## Scheduled Health Checks

- For recurring health checks in the current chat, use the built-in `cron`
  tool.
- Do not use `HEARTBEAT.md` for the chat-bound health checks in this lab.
- Keep scheduled reports short and concrete.
- If there are no recent backend errors in the requested window, say the
  system looks healthy.
- If the user asks to list or remove scheduled jobs, use the `cron` tool
  directly.
