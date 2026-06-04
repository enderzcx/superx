---
half_life: 30d
archive_at: 2026-07-04
---

# Grok Bridge Plan

`superx research` solves the one-shot research loop:

```text
Codex writes prompt -> user pastes to web Grok -> user pastes result back
```

It should not become a full Grok collaboration bridge. `superx` stays focused on X/Twitter retrieval plus X-first research.

## Recommended Separate Tool

Create a separate CLI later, tentatively named `grb` or `grok-bridge`, modeled after `crb`:

```bash
grb ask "quick question"
grb consult "second opinion on this plan"
grb research "source-backed research brief"
grb delegate --mode adversarial-review "review this approach"
grb status <job-id>
grb result <job-id>
grb cancel <job-id>
grb continue <job-id> "follow up on this point"
```

## Artifact Contract

Each job should write durable files:

```text
.grok-bridge/jobs/<job-id>/
  prompt.md
  result.md
  raw.json
  meta.json
```

`meta.json` should include command, mode, timestamps, model/runtime info when available, exit code, timeout, and source file paths passed by Codex.

## Key Decisions

- Keep `superx research` foreground and one-shot.
- Put background jobs, status/result/cancel, and follow-up sessions in `grb`.
- Store artifacts outside `.superx/` so X retrieval cache and Grok collaboration jobs do not mix.
- Start with CLI before MCP. Add MCP only after the command and artifact contract settle.

## Non-Goals For superx

- No long-running job manager.
- No durable multi-turn Grok session management.
- No generic `delegate` / review modes.
- No attempt to make `superx` a universal model bridge.
