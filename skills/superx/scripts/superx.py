#!/usr/bin/env python3
"""
superx: Thin wrapper to expose Grok Build's native X/Twitter tools
(x_user_search, x_keyword_search, x_semantic_search, x_thread_fetch)
and one-shot Grok research capability to local agents like Codex via simple CLI.

Core X commands (structured, high-quality, no browser):
  superx user "xAI" --count 5
  superx semantic "new Grok model release" --limit 5 --from-date 2026-04-01
  superx keyword 'from:xai min_faves:500' --mode Latest --limit 10
  superx thread 1661523610111193088   # or full https://x.com/.../status/...
  superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20'  # caches to .superx/articles/

One-shot research (solves the "Codex generate prompt -> paste to web Grok -> paste back" loop):
  superx research "调研 2026 年 AI agent 如何更好使用 Grok Build 原生 X 工具和本地集成"

The X-specific commands force single-tool structured JSON output.
The research command runs one-shot Grok research (web + X tools) and returns clean Markdown, auto-cached to .superx/research/.

Requires: grok CLI in PATH or at ~/.local/bin/grok, and authenticated (XAI_API_KEY or login).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

def resolve_bin(env_name: str, default_name: str) -> str:
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value
    local_bin = Path.home() / ".local" / "bin" / default_name
    if local_bin.exists():
        return str(local_bin)
    return shutil.which(default_name) or default_name

GROK_BIN = resolve_bin("GROK_BIN", "grok")
OPENCLI_BIN = resolve_bin("OPENCLI_BIN", "opencli")


def strip_ansi(value: str) -> str:
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value or "")


def trim_text(value: str, max_len: int = 4000) -> str:
    value = strip_ansi(value or "")
    return value if len(value) <= max_len else value[-max_len:]


def coerce_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_grok_headless(prompt: str, max_turns: int = 4, timeout: int = 120, print_errors: bool = True, include_internal: bool = False) -> dict:
    """Run grok -p with yolo, capture the json output."""
    cmd = [
        GROK_BIN,
        "-p", prompt,
        "--yolo",
        "--output-format", "json",
        "--max-turns", str(max_turns),
        "--no-auto-update",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        print(f"Error: grok binary not found: {GROK_BIN}", file=sys.stderr)
        sys.exit(127)
    except subprocess.TimeoutExpired:
        print(f"Error: grok timed out after {timeout}s", file=sys.stderr)
        sys.exit(1)

    if proc.returncode != 0:
        if print_errors:
            print(f"grok exited {proc.returncode}", file=sys.stderr)
            if proc.stderr:
                print(trim_text(proc.stderr.strip()), file=sys.stderr)
        # still try to parse stdout if any
    stdout = (proc.stdout or "").strip()
    if not stdout:
        print("Error: no output from grok", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(stdout)
        if include_internal and isinstance(data, dict):
            data["_superx_grok_returncode"] = proc.returncode
            if proc.stderr:
                data["_superx_grok_stderr"] = trim_text(proc.stderr.strip())
        return data
    except json.JSONDecodeError:
        print("Warning: grok output was not JSON, raw:", file=sys.stderr)
        print(stdout[:500], file=sys.stderr)
        fallback = {
            "text": stdout,
        }
        if include_internal:
            fallback["_superx_grok_returncode"] = proc.returncode
            fallback["_superx_grok_stderr"] = trim_text(proc.stderr.strip()) if proc.stderr else ""
        return fallback


def run_grok_plain(
    prompt: str,
    max_turns: int = 8,
    timeout: int = 900,
    model: str = None,
    effort: str = None,
    reasoning_effort: str = None,
    session_id: str = None,
    check: bool = False,
) -> dict:
    cmd = [
        GROK_BIN,
        "-p", prompt,
        "--yolo",
        "--max-turns", str(max_turns),
        "--no-auto-update",
    ]
    if model:
        cmd.extend(["-m", model])
    if effort:
        cmd.extend(["--effort", effort])
    if reasoning_effort:
        cmd.extend(["--reasoning-effort", reasoning_effort])
    if session_id:
        cmd.extend(["-r", session_id])  # resume an existing Grok session for follow-up
    if check:
        cmd.append("--check")  # self-verification loop, expert double-check
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return {
            "text": "",
            "_superx_grok_returncode": 127,
            "_superx_grok_stderr": f"grok binary not found: {GROK_BIN}",
        }
    except subprocess.TimeoutExpired as exc:
        stderr = coerce_text(exc.stderr)
        timeout_note = f"grok timed out after {timeout}s"
        stderr = f"{stderr}\n{timeout_note}" if stderr else timeout_note
        partial_stdout = getattr(exc, "stdout", None)
        if partial_stdout is None:
            partial_stdout = getattr(exc, "output", None)
        return {
            "text": coerce_text(partial_stdout),
            "_superx_grok_returncode": 124,
            "_superx_grok_stderr": trim_text(stderr),
        }
    return {
        "text": proc.stdout or "",
        "_superx_grok_returncode": proc.returncode,
        "_superx_grok_stderr": trim_text(proc.stderr.strip()) if proc.stderr else "",
    }


def extract_text(result: dict) -> str:
    if isinstance(result, dict):
        if "text" in result:
            return result.get("text") or ""
        if "result" in result:
            return result.get("result") or ""
    return str(result)

def parse_json_text(text: str):
    return json.loads(text)

def normalize_post_id(value: str) -> str:
    value = str(value).strip()
    patterns = [r"/status/(\d+)", r"/i/status/(\d+)", r"/i/article/(\d+)"]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    match = re.search(r"\b(\d{10,})\b", value)
    return match.group(1) if match else value

def safe_slug(value: str, max_len: int = 80) -> str:
    value = re.sub(r"[^\w\s.-]+", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = value.strip(".-")
    return (value[:max_len].strip(".-") or "x-article")

def default_cache_dir(cache_dir=None) -> Path:
    if cache_dir:
        return Path(cache_dir).expanduser()
    env_dir = os.environ.get("SUPERX_CACHE_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.cwd() / ".superx"

def cache_file_for_article(post_id: str, title: str = "x-article", cache_dir=None) -> Path:
    return default_cache_dir(cache_dir) / "articles" / f"{post_id}-{safe_slug(title)}.md"

def find_cached_article(post_id: str, cache_dir=None):
    article_dir = default_cache_dir(cache_dir) / "articles"
    matches = sorted(article_dir.glob(f"{post_id}-*.md"))
    return matches[0] if matches else None

def run_opencli_article(source: str) -> dict:
    cmd = [OPENCLI_BIN, "twitter", "article", source, "-f", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"opencli article failed: {err}")
    stdout = (proc.stdout or "").strip()
    data = json.loads(stdout)
    if isinstance(data, list):
        if not data:
            raise RuntimeError("opencli article returned an empty list")
        return data[0]
    return data

def pick_post(data):
    if isinstance(data, dict):
        for key in ("requestedPost", "mainPost"):
            post = data.get(key)
            if isinstance(post, dict):
                return post
        if "content" in data or "text" in data:
            return data
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return first
    return {}

def compact_article_from_grok(data: dict, source: str, post_id: str):
    if isinstance(data, dict) and data.get("error"):
        return None
    post = pick_post(data)
    content = (post.get("content") or post.get("text") or "").strip()
    if not content or re.fullmatch(r"https?://t\.co/\S+", content):
        return None
    first_line = next((line.strip("# ").strip() for line in content.splitlines() if line.strip()), "X article")
    return {
        "id": str(post.get("id") or post_id),
        "title": first_line[:120],
        "author": post.get("author") or "",
        "url": source,
        "content": content,
        "engagement": post.get("engagement"),
        "fetched_via": "grok:x_thread_fetch",
    }

def markdown_for_article(article: dict) -> str:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    title = (article.get("title") or "X article").strip()
    author = article.get("author") or ""
    url = article.get("url") or ""
    via = article.get("fetched_via") or "unknown"
    lines = [
        f"# {title}",
        "",
        f"- Source: {url}",
        f"- Author: {author}",
        f"- Fetched: {fetched_at}",
        f"- Fetcher: {via}",
    ]
    engagement = article.get("engagement")
    if isinstance(engagement, dict):
        metric_bits = [f"{k}={v}" for k, v in engagement.items() if v is not None]
        if metric_bits:
            lines.append(f"- Metrics: {', '.join(metric_bits)}")
    lines.extend(["", article.get("content", "").strip(), ""])
    return "\n".join(lines)

def save_markdown(md: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    return path

def force_tool_prompt(tool_name: str, params: dict, extra_instruction: str = "") -> str:
    """Build a prompt that forces the agent to call exactly one tool and return only its result."""
    params_str = ", ".join(f'{k}={json.dumps(v)}' for k, v in params.items() if v is not None)
    return f"""You are a strict tool executor. Do not chat, do not explain, do not add any text outside the final JSON.

IMMEDIATELY call the built-in tool named "{tool_name}" with exactly these parameters:
{params_str}

{extra_instruction}

After the tool result is returned in your context, your VERY NEXT (and final) output must be ONLY the raw tool result as valid compact JSON. 
- No ```json fences
- No "Here is the result:" prefix
- No extra sentences
- If the tool returned an error or empty list, still emit the JSON object or array as-is.
- If multiple items, emit a JSON array or object exactly as the tool gave it.
Output nothing else.""" 

def fetch_thread_data(post_id: str) -> dict:
    params = {"post_id": str(post_id)}
    prompt = force_tool_prompt("x_thread_fetch", params)
    res = run_grok_headless(prompt)
    text = extract_text(res)
    return parse_json_text(text)

def cmd_user(args):
    params = {"query": args.query, "count": args.count}
    prompt = force_tool_prompt("x_user_search", params)
    res = run_grok_headless(prompt)
    text = extract_text(res)
    # try to pretty print if it looks like json
    try:
        data = json.loads(text)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        print(text)

def cmd_semantic(args):
    params = {
        "query": args.query,
        "limit": args.limit,
        "from_date": args.from_date,
        "to_date": args.to_date,
        "min_score_threshold": args.min_score,
    }
    # filter None
    params = {k: v for k, v in params.items() if v is not None}
    prompt = force_tool_prompt("x_semantic_search", params)
    res = run_grok_headless(prompt)
    text = extract_text(res)
    try:
        data = json.loads(text)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        print(text)

def cmd_keyword(args):
    params = {
        "query": args.query,
        "limit": args.limit,
        "mode": args.mode,
        "from_date": args.from_date,
        "to_date": args.to_date,
    }
    params = {k: v for k, v in params.items() if v is not None}
    extra = "Use advanced X search syntax in the query (from:user, since:YYYY-MM-DD, min_faves:N, etc.). mode is Latest or Top."
    prompt = force_tool_prompt("x_keyword_search", params, extra)
    res = run_grok_headless(prompt)
    text = extract_text(res)
    try:
        data = json.loads(text)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        print(text)

def cmd_thread(args):
    data = fetch_thread_data(args.post_id)
    print(json.dumps(data, ensure_ascii=False, indent=2))

def cmd_article(args):
    post_id = normalize_post_id(args.source)
    cached = find_cached_article(post_id, args.cache_dir)
    if cached and not args.force:
        if args.format == "json":
            print(json.dumps({"cache_hit": True, "markdown_path": str(cached)}, ensure_ascii=False, indent=2))
        elif args.path_only:
            print(cached)
        else:
            print(cached.read_text(encoding="utf-8"))
        return

    article = None
    errors = []
    if args.source_mode in ("auto", "grok"):
        try:
            article = compact_article_from_grok(fetch_thread_data(post_id), args.source, post_id)
        except SystemExit as exc:
            errors.append(f"grok exited {exc.code}")
        except Exception as exc:
            errors.append(f"grok: {exc}")
        if args.source_mode == "grok" and article is None:
            print(json.dumps({"error": "grok did not return article content", "details": errors}, ensure_ascii=False, indent=2))
            sys.exit(1)

    if article is None and args.source_mode in ("auto", "opencli"):
        try:
            item = run_opencli_article(args.source)
            article = {
                "id": post_id,
                "title": item.get("title") or "X article",
                "author": item.get("author") or "",
                "url": item.get("url") or args.source,
                "content": item.get("content") or "",
                "fetched_via": "opencli:twitter article",
            }
        except Exception as exc:
            errors.append(f"opencli: {exc}")

    if article is None:
        print(json.dumps({"error": "failed to fetch article", "details": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

    md = markdown_for_article(article)
    output_path = Path(args.output).expanduser() if args.output else cache_file_for_article(post_id, article.get("title") or "", args.cache_dir)
    if output_path.exists() and output_path.is_dir():
        output_path = output_path / cache_file_for_article(post_id, article.get("title") or "", args.cache_dir).name
    save_markdown(md, output_path)

    if args.format == "json":
        print(json.dumps({"cache_hit": False, "markdown_path": str(output_path), "article": article}, ensure_ascii=False, indent=2))
    elif args.path_only:
        print(output_path)
    else:
        print(md)


def clean_markdown_output(text: str) -> str:
    text = strip_ansi(text).strip()
    fence = re.fullmatch(r"```(?:markdown)?\s*\n?(?P<body>.*?)\n?```", text, flags=re.DOTALL)
    if fence:
        text = fence.group("body").strip()
    if not text.startswith("#"):
        first_heading = re.search(r"(?m)^#{1,6}\s+\S", text)
        preamble = text[:first_heading.start()].strip() if first_heading else ""
        if first_heading and "```" not in preamble:
            text = text[first_heading.start():]
    return text.strip()


def build_research_prompt(query: str, *, effort: str = None, session_id: str = None) -> str:
    """Turn headless grok into a one-shot (or session-continued) X-first researcher.
    The effort/session are mainly controlled at CLI level via --effort / --session-id,
    this prompt just sets the researcher persona and strict output contract.
    """
    context_note = ""
    if session_id:
        context_note = "\nThis is a continuation of an existing Grok session. Build on previous context if available via that session."
    effort_note = ""
    if effort and effort in ("high", "xhigh", "max"):
        effort_note = f"\nYou are operating in high-effort mode ({effort}). Be especially thorough, consider edge cases, cross-verify aggressively, and produce deeper analysis."

    return f"""You are a world-class, thorough researcher helping a local coding agent.

You have access to web search, open_page, X/Twitter native tools (x_user_search, x_semantic_search, x_keyword_search, x_thread_fetch), and any other tools available in this Grok environment.{effort_note}

Research task: {query}
{context_note}

Execution rules:
- Use tools proactively and iteratively when they improve the answer. Do multiple tool calls if needed.
- If the task is explicitly a simple connectivity, formatting, or no-tool smoke check, answer directly without forcing tool calls.
- For timely, community, or social signals, especially anything on X/Twitter, heavily leverage the native X tools because they are often superior.
- If the task is not X-related, use web and other available tools directly, but still keep the report source-backed.
- Prioritize primary sources, recent high-signal content, official docs, and direct data.
- Cross-verify important claims.
- Keep precise URLs for every key fact or quote.

Output rules (strict):
- When research is complete, output ONLY the final report as clean, professional Markdown.
- Do NOT prefix with "Here is the research report", "```markdown", or any meta text.
- Do NOT add closing remarks after the report.
- Structure with clear headings, e.g.:
  # [Good Title]
  ## Executive Summary
  ## Key Findings
  - bullets
  ## Detailed Insights / Analysis
  ## Sources and References
  - [Title](url)
- Make the report directly usable by an AI coding agent or human builder (actionable, with links, data where relevant).

Start now. Use tools when they are useful. When finished, emit only the Markdown."""


def cmd_research(args):
    query = args.query.strip()
    if not query:
        print("Error: research query is empty", file=sys.stderr)
        sys.exit(2)
    if args.timeout <= 0:
        print("Error: --timeout must be > 0", file=sys.stderr)
        sys.exit(2)
    if args.retries < 0:
        print("Error: --retries must be >= 0", file=sys.stderr)
        sys.exit(2)

    prompt = build_research_prompt(
        query,
        effort=getattr(args, 'effort', None),
        session_id=getattr(args, 'session_id', None),
    )
    res = {}
    text = ""
    attempts = args.retries + 1
    for attempt in range(1, attempts + 1):
        res = run_grok_plain(
            prompt,
            max_turns=args.max_turns,
            timeout=args.timeout,
            model=args.model,
            effort=args.effort,
            reasoning_effort=getattr(args, 'reasoning_effort', None),
            session_id=getattr(args, 'session_id', None),
            check=getattr(args, 'check', False),
        )
        text = clean_markdown_output(extract_text(res))
        if isinstance(res, dict) and int(res.get("_superx_grok_returncode", 0) or 0) == 127:
            break
        if text or attempt == attempts:
            break
    grok_returncode = int(res.get("_superx_grok_returncode", 0) or 0) if isinstance(res, dict) else 0
    grok_stderr = res.get("_superx_grok_stderr", "") if isinstance(res, dict) else ""
    if not text:
        if grok_returncode == 127 and grok_stderr:
            print(f"Error: {grok_stderr}", file=sys.stderr)
            sys.exit(127)
        print(f"Error: grok research returned empty output after {attempts} attempt(s)", file=sys.stderr)
        if grok_stderr:
            print("grok stderr tail:", file=sys.stderr)
            print(trim_text(grok_stderr, 2000), file=sys.stderr)
        sys.exit(1)

    # Cache like articles
    cache_dir = default_cache_dir(args.cache_dir)
    research_dir = cache_dir / "research"
    slug = safe_slug(query)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{ts}-{slug}.md"
    if args.output:
        requested_output = Path(args.output).expanduser()
        if args.output.endswith(os.sep) or (requested_output.exists() and requested_output.is_dir()):
            output_path = requested_output / filename
        else:
            output_path = requested_output
    else:
        output_path = research_dir / filename
    save_markdown(text, output_path)

    metadata = {
        "query": query,
        "markdown_path": str(output_path),
        "metadata_path": str(output_path.with_suffix(".json")),
        "chars": len(text),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "max_turns": args.max_turns,
        "timeout": args.timeout,
        "attempts": attempt,
        "retries": args.retries,
        "fetcher": "grok:research",
        "grok_returncode": grok_returncode,
        "model": getattr(args, "model", None),
        "effort": getattr(args, "effort", None),
        "reasoning_effort": getattr(args, "reasoning_effort", None),
        "session_id": getattr(args, "session_id", None),
        "check": getattr(args, "check", False),
    }
    if grok_returncode != 0:
        metadata["warning"] = f"grok exited {grok_returncode}; research output may be partial"
        if grok_stderr:
            metadata["grok_stderr_tail"] = trim_text(grok_stderr, 2000)
    save_markdown(json.dumps(metadata, ensure_ascii=False, indent=2), output_path.with_suffix(".json"))

    if args.path_only:
        print(output_path)
    elif args.format == "json":
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    else:
        print(text)
    if grok_returncode != 0 and not args.allow_partial:
        print(f"Warning: grok exited {grok_returncode}; saved partial research to {output_path}", file=sys.stderr)
        sys.exit(grok_returncode)
    if grok_returncode != 0:
        print(f"Warning: grok exited {grok_returncode}; saved partial research to {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="superx",
        description="Call Grok Build native X tools and X-first Grok research from CLI / Codex / other agents."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # user
    p_user = sub.add_parser("user", help="x_user_search by name/handle")
    p_user.add_argument("query", help="search query e.g. xAI or elonmusk")
    p_user.add_argument("--count", type=int, default=3, help="1-10")
    p_user.set_defaults(func=cmd_user)

    # semantic
    p_sem = sub.add_parser("semantic", help="x_semantic_search natural language")
    p_sem.add_argument("query", help="natural language query")
    p_sem.add_argument("--limit", type=int, default=3)
    p_sem.add_argument("--from-date", dest="from_date")
    p_sem.add_argument("--to-date", dest="to_date")
    p_sem.add_argument("--min-score", type=float, dest="min_score")
    p_sem.set_defaults(func=cmd_semantic)

    # keyword (advanced syntax)
    p_kw = sub.add_parser("keyword", help="x_keyword_search with advanced operators")
    p_kw.add_argument("query", help='e.g. from:xai since:2026-05-01 min_faves:100')
    p_kw.add_argument("--limit", type=int, default=3)
    p_kw.add_argument("--mode", choices=["Latest", "Top"], default="Latest")
    p_kw.add_argument("--from-date", dest="from_date")
    p_kw.add_argument("--to-date", dest="to_date")
    p_kw.set_defaults(func=cmd_keyword)

    # thread
    p_th = sub.add_parser("thread", help="x_thread_fetch full conversation")
    p_th.add_argument("post_id", help="numeric tweet/post ID or full status URL")
    p_th.set_defaults(func=cmd_thread)

    # article
    p_article = sub.add_parser("article", help="Fetch an X long-form article/status body and cache it as Markdown")
    p_article.add_argument("source", help="numeric post/article ID or full X status/article URL")
    p_article.add_argument("--format", choices=["md", "json"], default="md")
    p_article.add_argument("--output", help="Markdown output file or directory. Defaults to ./.superx/articles/")
    p_article.add_argument("--cache-dir", help="Cache directory root. Defaults to ./.superx or SUPERX_CACHE_DIR.")
    p_article.add_argument("--path-only", action="store_true", help="print only the cached/saved Markdown path")
    p_article.add_argument("--force", action="store_true", help="ignore cache and fetch again")
    p_article.add_argument("--source-mode", choices=["auto", "grok", "opencli"], default="auto", help="fetcher order")
    p_article.set_defaults(func=cmd_article)

    # research - X-first one-shot research via Grok (web + native X tools etc.)
    p_research = sub.add_parser("research", help="One-shot Grok research optimized for X/frontier signals. Outputs Markdown and caches to .superx/research/. Supports effort/model/session to approximate web 'expert mode'.")
    p_research.add_argument("query", help="Research question or task")
    p_research.add_argument("--max-turns", type=int, default=10, help="Max agent turns (default 10 for heavy research; raise to 12+ for harder or self-checked research)")
    p_research.add_argument("--format", choices=["md", "json"], default="md")
    p_research.add_argument("--output", help="Custom output .md file path; existing directories or trailing slashes receive an auto-named file. Defaults to ./.superx/research/<ts>-<slug>.md")
    p_research.add_argument("--cache-dir", help="Cache root. Defaults to ./.superx or SUPERX_CACHE_DIR")
    p_research.add_argument("--path-only", action="store_true", help="print only the saved Markdown path")
    p_research.add_argument("--timeout", type=int, default=int(os.environ.get("SUPERX_RESEARCH_TIMEOUT", "900")), help="Grok subprocess timeout in seconds (default 900 or SUPERX_RESEARCH_TIMEOUT)")
    p_research.add_argument("--retries", type=int, default=int(os.environ.get("SUPERX_RESEARCH_RETRIES", "1")), help="Retry count when Grok returns no usable Markdown (default 1 or SUPERX_RESEARCH_RETRIES)")
    p_research.add_argument("--allow-partial", action="store_true", help="exit 0 even if grok exits non-zero after producing output")
    p_research.add_argument("--model", default="grok-build", help="Model to use (default grok-build for heavy research; see `grok models`)")
    p_research.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default="max", help="Effort level (default max for heavy/expert-like research)")
    p_research.add_argument("--reasoning-effort", dest="reasoning_effort", help="Reasoning effort (only for models that support it; grok-build does not)")
    p_research.add_argument("--session-id", dest="session_id", help="Existing Grok session ID (from `grok sessions list`) to resume for follow-up. Uses --resume; cannot create arbitrary names.")
    p_research.add_argument("--no-check", dest="check", action="store_false", default=True, help="Disable self-verification loop (enabled by default for heavy research)")
    p_research.set_defaults(func=cmd_research)

    args = parser.parse_args()
    # normalize post_id if URL passed
    if hasattr(args, "post_id") and args.post_id:
        if "status/" in args.post_id:
            args.post_id = args.post_id.rstrip("/").split("status/")[-1].split("?")[0]
        elif "/i/status/" in args.post_id:
            args.post_id = args.post_id.rstrip("/").split("/i/status/")[-1].split("?")[0]
    args.func(args)

if __name__ == "__main__":
    main()
