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
| `superx research` | 让 Grok 做一次性调研并保存 Markdown 报告 | Grok Build CLI，X 工具受账号权限限制 |
| `superx doctor` | 诊断本机 Grok/OpenCLI/model/X 工具可用性 | 本地 CLI 探测，可选 live X 工具 probe |

核心设计是三层：

- Grok-native：`user`、`keyword`、`semantic`、`thread` 直接调用 Grok Build 原生 X 工具，返回 JSON。
- Markdown cache：`article` 会把内容保存到当前项目的 `.superx/articles/`，后续 Agent 可以直接读文件，不用重复抓取同一个 URL。
- Research cache：`research` 会让 Grok 做一次性调研，把报告保存到 `.superx/research/`，旁边写入一份 metadata JSON。

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

`superx research` 是一次性 Grok 调研入口，用来替代“Codex 写 prompt -> 你复制到网页版 Grok -> 再复制结果回来”的中转流程。它会调用本地 Grok CLI，由 Grok 自己决定使用 web、open_page、原生 X 工具等能力，最后输出 Markdown 报告。

注意：`research` 不是通用 Grok 协作桥。它没有 background job、`status/result/cancel` 这类任务管理能力；`--session-id` 只能恢复 Grok 已有 session id，不能创建自定义命名会话。`research` 也没有 OpenCLI fallback；如果 Grok 调研过程中使用原生 X 工具，同样受 SuperGrok / X Premium+ 和 Grok Build 可用性限制。

## 安装

### 依赖

- Python 3.9+
- Grok Build CLI：<https://x.ai/cli>
- SuperGrok 或 X Premium+，用于 Grok-native X 工具
- 可选：[OpenCLI](https://github.com/jackwener/opencli)，用于 `article --source-mode opencli`

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

OpenCLI 仓库：<https://github.com/jackwener/opencli>

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

诊断本机环境：

```bash
superx doctor
superx doctor --format json
superx doctor --probe-x-tools
```

默认 `doctor` 不发起 live Grok 工具调用；`--probe-x-tools` 会用 `grok-build` 做一次 live probe，确认 `x_user_search`、`x_keyword_search`、`x_semantic_search`、`x_thread_fetch` 是否真的可用。

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

让 Grok 做一次性调研，并把报告保存到 `.superx/research/`。现在默认就是重度专家模式：

```bash
superx research "调研 Grok Build 原生 X 工具如何改变本地 Agent 工作流"
```

默认参数：`--max-turns 30`、`--timeout 3600`、`--model grok-build`、`--effort max`、自检开启。自检会让 Grok 在最终输出前多做一轮检查。

需要让 Grok CLI 自己开多个 subagents 并发做候选解时，显式加 `--best-of-n N`。例如请求 16 路 xhigh：

```bash
superx research "调研 Grok CLI multi-agent/best-of-n 对本地 agent 工作流的价值" --effort xhigh --best-of-n 16 --max-turns 45 --timeout 5400
```

`--best-of-n` 透传 Grok CLI 的 best-of-N tournament，只用于第一轮 primary run；如果后续需要 resume-finalizer 整理 Markdown，finalizer 不会继续开并发候选。当前本机 `grok models` 未列出 `grok-4.20-multi-agent-xhigh` 这个模型 ID；CLI 原生路线是 `--model grok-build --effort xhigh --best-of-n 16`。实际候选数量由当前 Grok CLI 决定；本机 smoke 中请求 16 时，tournament 输出汇报了 10 个候选。

如果第一轮因为 `Max turns reached` 没有产出可保存 Markdown，默认第二轮会接上同一个工作目录里的 Grok 最近 session（等价 `grok -r`）做 finalize-only：禁用工具（`--tools ""`）、不继续找资料、关闭自检、`--max-turns 6`、保留原 effort/model，只把已有上下文整理成 Markdown。

只返回保存后的 Markdown 路径，方便 Codex 继续读取：

```bash
superx research "最近 X 上关于本地 AI agent 的高信号讨论" --path-only
```

返回 JSON 元数据：

```bash
superx research "SuperX 和 OpenCLI 的能力边界怎么写清楚" --format json
```

自定义保存位置，或给特别宽的题目继续加预算：

```bash
superx research "Grok Build CLI 最新实践案例" --output ./notes/grok-build-research.md
superx research "跨多个生态调研 agent harness 设计" --timeout 5400 --max-turns 45
```

`--output` 默认按 Markdown 文件路径处理；如果传入已存在的目录，或路径以 `/` 结尾，`superx` 会在该目录里生成自动命名的报告文件。

默认已经给足重度预算。只有题目特别宽时再提高 turns：

```bash
superx research "调研 AI agent 使用 Grok Build 原生 X 工具的最佳实践" --max-turns 45 --path-only
```

想轻一点可以关闭自检或降低 effort：

```bash
superx research "快速了解 X 上关于 Grok Build 的最新讨论" --no-check --effort high
```

明确不要自动 resume-finalizer：

```bash
superx research "快速 smoke 一下 Grok CLI" --no-retry --no-check --effort low --max-turns 3
```

手动把已有 Grok session 收口成 Markdown：

```bash
superx research "把当前 session 已有上下文整理成最终报告" --finalize-only --session-id 019e...
```

需要更精细控制 Grok CLI 工具面时，可以只影响 primary research run：

```bash
superx research "只做 X 侧信号，不跑 shell" --tools web_search,x_keyword_search,x_semantic_search --disallowed-tools run_terminal_command
superx research "只基于当前 session 上下文整理，不再 web 搜索" --disable-web-search --no-check
```

这些高级工具开关只透传给第一轮 primary run；默认 resume-finalizer 和 `--finalize-only` 都会禁用工具（`--tools ""`）并只整理已有上下文。

参数边界：

- `--effort low|medium|high|xhigh|max` 会透传给 Grok CLI，默认 `max`。
- `--best-of-n N` 会透传 Grok CLI 的 best-of-N subagent tournament，建议先用 4 验证，再请求 16；实际 fan-out 可能受 Grok CLI 上限影响。它会更慢、更耗额度，也更依赖当前 cwd 是正常 git 工作树。
- `--no-check` 会关闭默认自检；默认开启自检，建议保留给重度调研。
- `--model` 可用 `grok models` 查看；默认 `grok-build`，当前本机也看到 `grok-composer-2.5-fast`。
- `--session-id` 使用 Grok CLI 的 `-r/--resume`，只能恢复 `grok sessions list` 里已有的真实 session id，不会创建自定义命名 session。
- `--reasoning-effort` 只适合支持 reasoning effort 的模型；当前 `grok-build` 会返回 400，不建议和默认模型一起使用。
- `--retries` 只处理“没有可保存 Markdown”的情况；默认 `1` 表示 heavy 尝试命中 `Max turns reached` 后自动接同一个 Grok session 做 finalize-only。它不是账号权限、rate limit 或无会员 fallback。
- `--no-retry` 会关闭默认空输出/max-turns 后的自动 resume-finalizer。
- `--finalize-only` 只恢复已有/最近 Grok session 并输出最终 Markdown，不继续 discovery，不调用工具，不再自动 retry；它不能和 `--best-of-n` 同用。
- `--tools`、`--disallowed-tools`、`--disable-web-search` 是 Grok CLI 高级开关，只作用于 primary research run。
- 不要在同一个工作目录里并发跑多个 `superx research`；默认 finalizer 使用裸 `grok -r`，会恢复该 cwd 最近 session。

## 没有 SuperGrok / X Premium+ 怎么办

先讲清楚：没有 SuperGrok / X Premium+ 时，`superx user`、`superx keyword`、`superx semantic`、`superx thread` 这些 Grok-native 命令不可用。

可以使用的公开或本地登录路线是：

- `superx article <url> --source-mode opencli`：当前 repo 内已实现的 fallback，会把 article/status 正文写成 Markdown。
- `r.jina.ai`：适合把部分公开网页或公开 X URL 转成 Markdown，取决于目标页面是否可访问。
- [`opencli twitter article|thread|profile|search`](https://github.com/jackwener/opencli)：适合配合本地 Chrome/X 登录态抓取可见内容。
- `fetch-x` skill：如果你在支持该 skill 的本地 Agent 环境中，可继续用它的 proxy + opencli 路由。

这些路线解决的是“公开或本地登录可见内容怎么取”，不是“怎样获得 Grok 原生 X 工具”。

`superx research` 没有无会员 fallback。它依赖本地 Grok CLI；如果研究任务需要 Grok 原生 X 工具，也会受 SuperGrok / X Premium+ 限制。

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

`superx research` 默认把报告保存到：

```text
your-project/
  .superx/
    research/
      20260604-020000-grok-build-x-tools.md
      20260604-020000-grok-build-x-tools.json
      _failed/
        20260604-021500-wide-topic.stdout
        20260604-021500-wide-topic.stderr
        20260604-021500-wide-topic.json
```

其中 `.md` 是报告正文，旁边 `.json` 是 metadata，包含 query、路径、时间、turns、timeout、attempts、model、effort、session、check 和 `attempt_details`。连续空输出失败时不会假装成功，会把每轮 raw stdout/stderr 和 attempt metadata 写到 `_failed/`。

## Agent 用法

对 Codex、Claude、Cursor 这类 Agent 来说，最简单的集成就是 shell 调用：

```bash
superx doctor --format json --no-update-check
superx keyword 'from:xai since:2026-05-01 min_faves:200' --mode Latest --limit 5
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --path-only
superx research '调研最近 X 上关于 Grok Build 的高信号讨论' --path-only
```

诊断和搜索命令返回 JSON，Agent 可以直接解析。`article --path-only` 和 `research --path-only` 返回 Markdown 文件路径，Agent 可以继续读取本地文件。

在本机 Codex 环境中，配套 skill 名也叫 `superx`。公开仓库用户不需要这个本地 skill，也可以直接用 CLI。

## 命令参考

```text
superx user <query> [--count N]
superx semantic <query> [--limit N] [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD] [--min-score FLOAT]
superx keyword <query> [--limit N] [--mode Latest|Top] [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD]
superx thread <post-id-or-status-url>
superx article <post-id-or-status-url> [--format md|json] [--path-only] [--force] [--output PATH] [--cache-dir DIR] [--source-mode auto|grok|opencli]
superx research <query> [--max-turns N] [--format md|json] [--path-only] [--timeout SEC] [--retries N] [--no-retry] [--allow-partial] [--output PATH] [--cache-dir DIR] [--model MODEL] [--effort low|medium|high|xhigh|max] [--best-of-n N] [--reasoning-effort EFFORT] [--session-id SESSION_ID] [--tools TOOLS] [--disallowed-tools TOOLS] [--disable-web-search] [--finalize-only] [--no-check]
superx doctor [--format text|json] [--model MODEL] [--probe-x-tools] [--timeout SEC] [--no-update-check]
```

## 常见问题

### `grok: command not found`

安装 Grok Build CLI，并确认它在 `PATH` 中。官方入口：<https://x.ai/cli>

`superx` 找不到 `grok` 时会退出 `127`，并打印 `grok binary not found`。

### `Error: grok timed out`

可以重试、降低 `--limit`，或者在抓 X article/status 时使用：

```bash
superx article <url> --source-mode opencli
```

如果是 `research` 超时，可以提高超时，或在确实只要轻量结果时降低 turns：

```bash
superx research <query> --timeout 5400 --max-turns 45
superx research <query> --no-check --effort high --max-turns 12
```

也可以设置环境变量：

```bash
export SUPERX_RESEARCH_TIMEOUT=5400
```

如果 Grok CLI 命中 `Max turns reached` 后没有最终 Markdown，`superx research` 默认会重试 1 次。第二轮会自动 resume 最近 Grok session 做 finalize-only：禁用工具，只把已收集上下文整理成最终报告。可以显式调整：

```bash
superx research <query> --retries 2
export SUPERX_RESEARCH_RETRIES=2
```

`--retries` 只处理“没有可保存 Markdown”的情况，不能替代账号权限、rate limit 或内容可见性。连续失败时查看 `.superx/research/_failed/*.json`、`.stdout`、`.stderr` 复盘每轮参数和 Grok 原始输出。

要完全关闭这类自动收口：

```bash
superx research <query> --no-retry
```

如果 Grok 已经产出内容但 CLI 返回非零退出码（例如 `max turns reached` 或 timeout），`superx research` 会保存 Markdown 和 metadata，并默认用非零码退出。确认要接受 partial 结果时加：

```bash
superx research <query> --allow-partial
```

### 自检后 max turns reached

默认自检会消耗额外 turns，但默认已经是 30 turns / 3600s。更复杂的调研可以提高到 45：

```bash
superx research <query> --max-turns 45
```

如果看到 empty output，保持默认 retries 通常会自动跑 resume-finalizer。手动收口最近 Grok session 可以用：

```bash
superx research <query> --finalize-only
superx research <query> --finalize-only --session-id 019e...
```

`--finalize-only` 使用已有/最近 Grok session，只整理上下文，不调用工具。

### 找不到 `x_user_search` / 不确定 X 工具是否可用

先跑诊断：

```bash
superx doctor
superx doctor --probe-x-tools
```

`doctor` 会检查 `grok`、`opencli`、`grok version`、`grok models` 和可选的 live X 工具 probe。`--probe-x-tools` 需要一次真实 Grok 调用；没有 SuperGrok / X Premium+ 或模型不含原生 X 工具时，probe 会明确失败。

### `reasoningEffort` 400

这表示当前模型不支持 `--reasoning-effort`。本机默认 `grok-build` 已实测会返回 400。去掉该参数，或换成真正支持 reasoning effort 的模型。

### `article` 只拿到一个 `t.co` 链接

这通常是 X article 的壳内容。可以强制 OpenCLI 路径：

```bash
superx article <url> --source-mode opencli
```

### OpenCLI fallback 失败

先确认 [OpenCLI](https://github.com/jackwener/opencli) 可用：

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
- `research` 是一次性调研报告，不是 `crb` 那种可管理的协作桥；没有后台任务、状态查询、取消。
- `research --best-of-n N` 使用 Grok CLI 原生 best-of-N subagent tournament；它不是新的模型 ID，也不会在 resume-finalizer 阶段继续并发。
- `--session-id` 只能恢复已有 Grok session id，不会创建命名会话；网页式随意连续聊天仍然更适合未来 `grb` 或 Grok 网页。
- `research` 没有 OpenCLI fallback；它依赖 Grok CLI，且使用原生 X 工具时仍受账号权限限制。
- `--reasoning-effort` 取决于模型支持情况；当前 `grok-build` 不支持。
- `research` 默认会对 max-turns 后的空输出重试 1 次；第二轮 resume 最近 Grok session 做 finalize-only，并传 `--tools ""` 禁用工具，不是权限或 rate limit fallback。
- `--tools`、`--disallowed-tools`、`--disable-web-search` 只作用于 primary research run；finalizer 始终偏向“只整理已有上下文”。
- `research` 遇到 Grok 非零退出码时会把已有内容标记为 partial；默认非零退出，`--allow-partial` 才会放行。
- `doctor --probe-x-tools` 是诊断，不能突破权限；probe 结果仍受账号、模型和 Grok Build 当前工具面限制。
- X 权限、内容可见性、账号状态、rate limit 都会影响结果。

## 维护

- 仓库根目录的 `superx.py` 是唯一实现源。
- `skills/superx/scripts/superx.py` 只是薄 launcher，用来避免 skill 内复制一份 wrapper 后发生漂移。
- 本机安装版 skill 的 launcher 会优先使用 `SUPERX_SOURCE`，默认指向这个仓库的 `superx.py`；移动源码目录后更新该环境变量或重建 symlink。

## License

MIT
