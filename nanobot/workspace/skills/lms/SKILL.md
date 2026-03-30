---
name: lms
description: Use LMS MCP tools for live course data
always: true
---

# LMS Skill

Use the LMS MCP tools for live backend data. Prefer tool-backed answers over
guesses or repository docs when the user asks about labs, scores, pass rates,
completion, groups, timelines, learners, or LMS health.

## Tool map

- `lms_health`: check backend health and item count.
- `lms_labs`: list available labs; call this first when a lab choice is needed.
- `lms_learners`: list learners registered in the LMS.
- `lms_pass_rates`: get per-task average score and attempt count for a lab.
- `lms_timeline`: get submission timeline for a lab.
- `lms_groups`: get group performance for a lab.
- `lms_top_learners`: get top learners for a lab; use a small limit unless the user asks for more.
- `lms_completion_rate`: get passed vs total for a lab.
- `lms_sync_pipeline`: trigger a sync only when data seems missing or stale, or when the user explicitly asks to sync.

## Strategy

- For live LMS questions, use the relevant `lms_*` tool instead of answering from memory.
- If the user asks about scores, pass rates, completion, groups, timelines, or top learners without naming a lab, call `lms_labs` first.
- If multiple labs are available, ask the user to choose one instead of guessing.
- When the current channel supports interactive choices, let the shared `structured-ui` skill present the lab options.
- Use the lab title as the default user-facing label and the lab identifier as the value.
- If the backend looks empty or a lab query returns no data, call `lms_health`.
- If the backend is healthy but data appears missing, trigger `lms_sync_pipeline` and retry once.
- Do not expose backend API keys or internal authentication details.

## Response style

- Keep answers concise and concrete.
- Format percentages with `%` and counts as plain numbers.
- Lead with the main result, then include a short supporting summary when needed.
- When the user asks what you can do, explain that you can answer live LMS questions about labs, health, pass rates, completion, groups, timelines, and top learners via MCP tools.
