# superx

`superx` 是一个给 Agent 用的 X/Twitter 数据 CLI：通过 Grok Build 原生 X 工具做用户搜索、关键词搜索、语义搜索和线程获取，并把 X 长文/帖子正文缓存成项目内 Markdown。

> 这不是 xAI 或 X 的官方项目。它是围绕 Grok Build CLI 构建的社区封装。

## 一句话

把 X 变成 Agent 可以直接调用、可以复用、可以落盘的资料入口。

适合 Codex、Claude、Cursor、本地自动化脚本，或者任何能执行 shell 命令的 Agent。

## 能做什么

| 命令 | 能力 | 主要依赖 |
|---|---|---|
| `superx user` | 按名字、关键词、handle 类查询搜索用户 | Grok Build 原生 `x_user_search` |
| `superx keyword` | 使用 X 高级搜索语法查帖 | Grok Build 原生 `x_keyword_search` |
| `superx semantic` | 用自然语言语义搜索相关帖子 | Grok Build 原生 `x_semantic_search` |
| `superx thread` | 获取完整线程、父帖、回复、指标等 | Grok Build 原生 `x_thread_fetch` |
| `superx article` | 获取 X status/article 正文并保存为 Markdown | Grok 优先，可用 OpenCLI 作为文章 fallback |

核心设计是两层：

- Grok-native：`user`、`keyword`、`semantic`、`thread` 直接调用 Grok Build 原生 X 工具，返回 JSON。
- Markdown cache：`article` 会把内容保存到当前项目的 `.superx/articles/`，后续 Agent 可以直接读文件，不用重复抓取同一个 URL。

## 能力边界

`superx` 不会规避登录、订阅、权限、X 可见性、rate limit 或 Grok Build 限制。

Grok-native 的四个命令：

- `superx user`
- `superx keyword`
- `superx semantic`
- `superx thread`

都依赖 Grok Build CLI 和账号可用的原生 X 工具。你需要 SuperGrok 订阅或 X Premium+ 账号，并且该账号能访问 Grok Build 原生 X 工具。

如果没有 SuperGrok / X Premium+，不要期待这四个 Grok-native 命令继续可用。公共路线和 OpenCLI 可以抓一些公开或登录可见的 X 内容，但不会解锁 Grok 的 `x_*` 原生工具。

当前仓库内已实现的无 SuperGrok / X Premium+ 路径只有：

```bash
superx article <url> --source-mode opencli
```

它用于抓取公开或本地登录可见的 X article/status 正文，并继续写入 Markdown 缓存。`user`、`keyword`、`semantic`、`thread` 目前没有内置 OpenCLI fallback。

## 安装

### 依赖

- Python 3.9+
- Grok Build CLI：<https://x.ai/cli>
- SuperGrok 或 X Premium+，用于 Grok-native X 工具
- 可选：OpenCLI，用于 `article --source-mode opencli`

Grok Build CLI 的安装方式以官方页面为准。安装后登录：

```bash
grok login
```

可以用一个最小命令确认 Grok CLI 可运行：

```bash
grok -p "hello" --yolo --max-turns 1 --output-format json --no-auto-update
```

如果需要 OpenCLI fallback：

```bash
npm install -g @jackwener/opencli
opencli twitter --help
```

安装 `superx`：

```bash
git clone https://github.com/enderzcx/superx.git
cd superx
python3 -m pip install .
superx --help
```

本地开发时也可以不安装，直接运行：

```bash
python3 superx.py --help
python3 superx.py user "xAI" --count 3
```

## 快速开始

搜索用户：

```bash
superx user "xAI" --count 3
```

语义搜索：

```bash
superx semantic "Grok Build Composer long running tasks" --limit 5 --from-date 2026-04-01
```

关键词搜索，支持 X 高级语法：

```bash
superx keyword 'from:xai since:2026-05-01 min_faves:200 filter:videos' --mode Latest --limit 8
```

获取完整线程：

```bash
superx thread 'https://x.com/xai/status/2061510464325206163'
```

抓取 X article/status 正文，并保存为 Markdown：

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20'
```

只返回保存后的 Markdown 路径：

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --path-only
```

返回 JSON 元数据：

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --format json
```

忽略缓存，强制重新抓取：

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --force
```

强制使用 OpenCLI article 路径：

```bash
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --source-mode opencli
```

## 没有 SuperGrok / X Premium+ 怎么办

先讲清楚：没有 SuperGrok / X Premium+ 时，`superx user`、`superx keyword`、`superx semantic`、`superx thread` 这些 Grok-native 命令不可用。

可以使用的公开或本地登录路线是：

- `superx article <url> --source-mode opencli`：当前 repo 内已实现的 fallback，会把 article/status 正文写成 Markdown。
- `r.jina.ai`：适合把部分公开网页或公开 X URL 转成 Markdown，取决于目标页面是否可访问。
- `opencli twitter article|thread|profile|search`：适合配合本地 Chrome/X 登录态抓取可见内容。
- `fetch-x` skill：如果你在支持该 skill 的本地 Agent 环境中，可继续用它的 proxy + opencli 路由。

这些路线解决的是“公开或本地登录可见内容怎么取”，不是“怎样获得 Grok 原生 X 工具”。

## 项目缓存

`superx article` 默认把 Markdown 保存到当前项目：

```text
your-project/
  .superx/
    articles/
      2061778310934516097-让你的agent从pi上长出来.md
```

这让 Agent 后续可以直接读取文件：

```bash
superx article <url> --path-only
```

自定义缓存根目录：

```bash
superx article <url> --cache-dir ./research/x
```

或者使用环境变量：

```bash
export SUPERX_CACHE_DIR="$PWD/.superx"
superx article <url>
```

如果文件已经存在，`superx article` 会直接返回缓存内容。需要重新抓取时加 `--force`。

默认不要提交 `.superx/`。只有当你明确想把研究产物作为仓库资料保留时，才把缓存文件纳入版本控制。

## Agent 用法

对 Codex、Claude、Cursor 这类 Agent 来说，最简单的集成就是 shell 调用：

```bash
superx keyword 'from:xai since:2026-05-01 min_faves:200' --mode Latest --limit 5
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --path-only
```

第一条返回 JSON，Agent 可以直接解析。第二条返回 Markdown 文件路径，Agent 可以继续读取本地文件。

在本机 Codex 环境中，配套 skill 名也叫 `superx`。公开仓库用户不需要这个本地 skill，也可以直接用 CLI。

## 命令参考

```text
superx user <query> [--count N]
superx semantic <query> [--limit N] [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD] [--min-score FLOAT]
superx keyword <query> [--limit N] [--mode Latest|Top] [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD]
superx thread <post-id-or-status-url>
superx article <post-id-or-status-url> [--format md|json] [--path-only] [--force] [--output PATH] [--cache-dir DIR] [--source-mode auto|grok|opencli]
```

## 常见问题

### `grok: command not found`

安装 Grok Build CLI，并确认它在 `PATH` 中。官方入口：<https://x.ai/cli>

### `Error: grok timed out`

可以重试、降低 `--limit`，或者在抓 X article/status 时使用：

```bash
superx article <url> --source-mode opencli
```

### `article` 只拿到一个 `t.co` 链接

这通常是 X article 的壳内容。可以强制 OpenCLI 路径：

```bash
superx article <url> --source-mode opencli
```

### OpenCLI fallback 失败

先确认 OpenCLI 可用：

```bash
npm install -g @jackwener/opencli
opencli twitter article <url> -f json
```

OpenCLI 是否能取到内容，取决于目标内容是否公开或你的本地浏览器/X 登录态是否可访问。

### 想用全局缓存

```bash
export SUPERX_CACHE_DIR="$HOME/.cache/superx"
```

## 限制

- Grok-native 命令依赖 Grok Build 原生工具，输出 schema 可能跟随 Grok 变化。
- `user` 是搜索，不是精确 profile resolver。
- `thread` 直接镜像 Grok 原生工具结果，字段可能随工具版本变化。
- `article` 会把正文归一化为 Markdown，但不会下载媒体文件。
- OpenCLI fallback 只覆盖当前 repo 内的 `article` 路径。
- X 权限、内容可见性、账号状态、rate limit 都会影响结果。

## License

MIT
