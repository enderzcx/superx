# superx

`superx` is a small CLI for agents that need structured X/Twitter data through Grok Build.

It wraps Grok Build's native X tools:

- `x_user_search`
- `x_keyword_search`
- `x_semantic_search`
- `x_thread_fetch`

It also adds an `article` command that saves long-form X article/status content as Markdown in the current project.

> This is not an official xAI or X project. It is a community wrapper around the Grok Build CLI.

## Why

Agents like Codex, Claude, Cursor, and local automation scripts often need X data in a shape they can reuse:

- search users by name or handle-like keywords
- search posts with X advanced search syntax
- run semantic searches over posts
- fetch post threads, replies, metrics, media URLs, and quoted posts
- save X long-form article content into local Markdown so the same source does not need to be fetched repeatedly

`superx` keeps that workflow as a CLI instead of forcing every agent to hand-write prompts to Grok.

## Requirements

You need:

- Grok Build CLI installed and logged in.
- A SuperGrok subscription or X Premium+ account that can use Grok Build and the native X tools.
- Python 3.9+.
- Optional: `opencli` for the `article` fallback path.

The Grok Build CLI page is here: <https://x.ai/cli>

It currently advertises:

```bash
curl -fsSL https://x.ai/cli/install.sh | bash
```

Then sign in:

```bash
grok login
grok -p "hello" --yolo --max-turns 1 --output-format json --no-auto-update
```

If `article` needs fallback support, install OpenCLI:

```bash
npm install -g @jackwener/opencli
opencli twitter --help
```

## Install

From source:

```bash
git clone https://github.com/enderzcx/superx.git
cd superx
python3 -m pip install .
superx --help
```

For local development without installing:

```bash
python3 superx.py --help
python3 superx.py user "xAI" --count 3
```

## Quick Start

Search users:

```bash
superx user "xAI" --count 3
```

Semantic search:

```bash
superx semantic "Grok Build Composer long running tasks" --limit 5 --from-date 2026-04-01
```

Keyword search with X advanced operators:

```bash
superx keyword 'from:xai since:2026-05-01 min_faves:200 filter:videos' --mode Latest --limit 8
```

Fetch a thread:

```bash
superx thread 'https://x.com/xai/status/2061510464325206163'
```

Fetch an X article/status body and cache it as Markdown:

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20'
```

Return only the saved Markdown path:

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --path-only
```

Return machine-readable metadata:

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --format json
```

Force a fresh fetch:

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --force
```

Force the OpenCLI article path:

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --source-mode opencli
```

## Project Cache

`article` saves Markdown into the current project by default:

```text
your-project/
  .superx/
    articles/
      2061778310934516097-让你的agent从pi上长出来.md
```

This lets agents read the saved Markdown later without fetching X again.

Use a custom cache root:

```bash
superx article <url> --cache-dir ./research/x
```

Or an environment variable:

```bash
export SUPERX_CACHE_DIR="$PWD/.superx"
superx article <url>
```

If the article file already exists, `superx article` returns the cached Markdown unless you pass `--force`.

## Command Reference

```text
superx user <query> [--count N]
superx semantic <query> [--limit N] [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD] [--min-score FLOAT]
superx keyword <query> [--limit N] [--mode Latest|Top] [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD]
superx thread <post-id-or-status-url>
superx article <post-id-or-status-url> [--format md|json] [--path-only] [--force] [--output PATH] [--cache-dir DIR] [--source-mode auto|grok|opencli]
```

## Agent Usage

For Codex/Claude/Cursor-style agents, the simplest integration is shell access:

```bash
superx keyword 'from:xai since:2026-05-01 min_faves:200' --mode Latest --limit 5
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --path-only
```

The first command returns JSON. The second returns a Markdown file path the agent can read from disk.

## Limitations

- `superx` does not bypass authentication, subscriptions, X permissions, rate limits, or Grok Build limits.
- Access to Grok Build's native X tools depends on your account and current Grok Build availability.
- `user` is search, not exact profile resolution. Searching `xAI` can return accounts with similar names.
- `thread` output schema can vary because it mirrors Grok's native tool result.
- `article` normalizes content into Markdown and falls back to OpenCLI when Grok thread fetch is slow or returns only an article shell.
- Media URLs are returned, but `superx` does not download media files.
- OpenCLI fallback may require a working browser/session depending on your local OpenCLI setup.

## Troubleshooting

`grok: command not found`

Install Grok Build CLI and make sure it is on `PATH`.

`Error: grok timed out`

Try the command again, lower the limit, or use `article --source-mode opencli` for X articles.

Article returns only a `t.co` link

That is an X article shell. Use:

```bash
superx article <url> --source-mode opencli
```

OpenCLI fallback fails

Install or update OpenCLI:

```bash
npm install -g @jackwener/opencli
opencli twitter article <url> -f json
```

Need a global cache instead of project-local cache

```bash
export SUPERX_CACHE_DIR="$HOME/.cache/superx"
```

## Local Codex Skill

The local Codex skill uses the same name: `superx`.

On this machine it lives at:

```text
~/.agents/skills/superx/
```

## License

MIT
