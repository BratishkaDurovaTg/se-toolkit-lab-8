# Tool Usage Notes

Tool signatures are provided automatically via function calling.
This file documents the non-obvious usage pattern for this lab.

## cron

- Use `cron` for chat-bound recurring health checks.
- Use `action: "add"` with `every_seconds` for short interval checks such as
  every 2 minutes.
- Put the whole future instruction into `message` so the scheduled run knows
  what to do.
- Good scheduled message pattern:
  `Check LMS/backend health for this chat using logs and traces from the last 2 minutes. Search recent backend errors first, inspect a matching trace if needed, and post a short summary here. If no recent backend errors exist, say the system looks healthy.`
- Use `action: "list"` when the user asks `List scheduled jobs.`
- Use `action: "remove"` with the known `job_id` when removing a test job.
- For Task 4, prefer `cron` over `HEARTBEAT.md`.
