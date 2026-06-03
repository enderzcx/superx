# superx Agent Instructions

## Project

`superx` is an open-source CLI and local agent skill for reading X/Twitter data through Grok Build native X tools, with a project-local Markdown cache for article/status content.

Public repo:

```text
https://github.com/enderzcx/superx
```

## Command Surface

```bash
superx user <query> [--count N]
superx semantic <query> [--limit N] [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD] [--min-score FLOAT]
superx keyword <query> [--limit N] [--mode Latest|Top] [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD]
superx thread <post-id-or-status-url>
superx article <post-id-or-status-url> [--format md|json] [--path-only] [--force] [--output PATH] [--cache-dir DIR] [--source-mode auto|grok|opencli]
```

## Capability Boundaries

Do not overclaim.

- Grok-native `user`, `keyword`, `semantic`, and `thread` depend on Grok Build CLI and the native X tools.
- The Grok-native path requires a SuperGrok subscription or X Premium+ account with Grok Build access.
- Without SuperGrok / X Premium+, do not claim the Grok-native `x_*` tools still work.
- No-membership fallback means using open/public routes:
  - `r.jina.ai` for public tweet/status/article Markdown when it works.
  - `opencli twitter thread|article|profile|search` with ordinary local Chrome/X login and Browser Bridge.
  - the existing `fetch-x` skill routing: proxy first, then opencli when article/replies/metrics are needed.
- In this repo, `superx article --source-mode opencli` is the implemented fallback path that can still write Markdown files when Grok article fetch is unavailable.

## Project Cache

`superx article` saves Markdown in the current project:

```text
.superx/articles/
```

Rules:

- Do not commit `.superx/` unless the user explicitly wants cached research artifacts committed.
- Prefer `superx article <url> --path-only` when another agent needs a reusable file path.
- Use `--force` only when you intentionally want a fresh fetch.
- Use `--cache-dir` or `SUPERX_CACHE_DIR` only when the user asks for a non-default cache location.

## Development Checks

Before saying a code/docs change is done, run the relevant checks:

```bash
python3 -m py_compile superx.py
python3 superx.py --help
python3 superx.py article 'https://x.com/0xenderzcx/status/2061778378089533835?s=20' --format json
python3 -m venv /tmp/superx-venv
/tmp/superx-venv/bin/python -m pip install .
/tmp/superx-venv/bin/superx --help
```

For README or public copy changes, also scan for stale names and overclaims:

```bash
rg -n "x-hound|grok-x|GROK_X|\\.x-hound|绕过|免费调用|不需要会员" .
```

## Publishing Rules

- Never commit credentials, API keys, cookies, browser profiles, or generated `.superx/` cache.
- Do not commit `*.egg-info/`, `dist/`, `build/`, `.venv/`, or `__pycache__/`.
- Public docs must say this is not an official xAI/X project.
- Public docs must link to the Grok Build CLI page (`https://x.ai/cli`) instead of inventing install commands.
- If describing no-membership usage, be precise: fallback routes can fetch public/login-visible X content, but they do not unlock Grok-native X tools.

