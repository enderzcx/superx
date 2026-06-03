#!/usr/bin/env python3
"""
superx: Thin wrapper to expose Grok Build's native X/Twitter tools
(x_user_search, x_keyword_search, x_semantic_search, x_thread_fetch)
to local agents like Codex via simple CLI.

Usage examples:
  superx user "xAI" --count 5
  superx semantic "new Grok model release" --limit 5 --from-date 2026-04-01
  superx keyword 'from:xai min_faves:500' --mode Latest --limit 10
  superx thread 1661523610111193088   # or full https://x.com/.../status/...
  superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20'

The wrapper forces Grok to call the exact tool and return ONLY the tool result as JSON.
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

def run_grok_headless(prompt: str, max_turns: int = 4) -> dict:
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
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("Error: grok timed out", file=sys.stderr)
        sys.exit(1)

    if proc.returncode != 0:
        print(f"grok exited {proc.returncode}", file=sys.stderr)
        if proc.stderr:
            print(proc.stderr.strip(), file=sys.stderr)
        # still try to parse stdout if any
    stdout = (proc.stdout or "").strip()
    if not stdout:
        print("Error: no output from grok", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print("Warning: grok output was not JSON, raw:", file=sys.stderr)
        print(stdout[:500], file=sys.stderr)
        return {"text": stdout}

def extract_text(result: dict) -> str:
    return result.get("text", "") or result.get("result", "") or str(result)

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

def main():
    parser = argparse.ArgumentParser(
        prog="superx",
        description="Call Grok Build native X tools from CLI / Codex / other agents."
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
