---
name: superx
description: "superx：包装本地 `superx` CLI 和 Grok Build 原生 X/Twitter 工具（x_user_search / x_keyword_search / x_semantic_search / x_thread_fetch）。Use when the task needs X/Twitter user search, keyword/semantic search, thread/article fetch, `.superx/articles` Markdown cache, or one-shot X-first/frontier research via `superx research`. Not for writing X posts, generic web research where official primary sources are required, browser screenshots, or continuous Grok collaboration."
when_to_use: "superx / 用 superx 搜 X / superx research / superx 调研 / superx X 工具 / x_user_search / x_keyword_search / x_semantic_search / x_thread_fetch / Grok Build X tools / X article Markdown 缓存 / 让 Codex 直接用 Grok 做研究 / 比网页 Grok copy-paste 更高效"
sunny_skill_type: wrapper
---

# superx

**Grok Build 原生 X 工具的 Codex / 本地 agent 包装层**。

Grok（xAI）内置 4 个高权限 X 工具，可直接返回结构化结果；相比浏览器抓取，更少遇到登录态、extension、页面反爬这类本地问题。

## 你当前拥有的 X 相关工具（Grok 侧）

**原生内置（本 skill 包装的核心）**：

- **x_user_search**  
  通过名字/关键词搜索 X 用户，返回 ID、@handle、粉丝数、简介、头像、认证状态。

- **x_keyword_search**  
  高级搜索语法（支持 `from:user`、`since:YYYY-MM-DD`、`min_faves:N`、`filter:images` 等所有 Twitter 高级操作符），可按作者、时间、热度、互动数精准筛选。支持 `mode=Latest|Top`。

- **x_semantic_search**  
  自然语言直接搜相关帖子（query 可以是句子），支持 `from_date`、`to_date`、`usernames` 过滤、`min_score_threshold`。

- **x_thread_fetch**  
  输入推文 numeric ID（或 status URL），返回完整对话链：原帖 + 父帖 + 所有 replies（含 metrics）。

**其他 X 相关能力（互补，非本 skill 重点）**：

- `fetch-x` skill（.agents/skills/fetch-x）：用 r.jina.ai proxy + opencli twitter thread/article，适合抓公开帖/长文，需 Chrome + extension 时会冲突诊断。
- `ender-x-style` skill：**写** X 帖/线程（Ender 个人语气），不是搜索。
- 通用 `web_search` / `open_page` / chrome-devtools MCP：可辅助，但 X 经常 402/挡匿名或需登录。
- 浏览器手动或 Playwright：兜底。

**推荐**：需要**搜索/发现/结构化数据**时优先 `superx`（本 skill）。需要**抓已知 URL 的正文+replies** 且 superx 不方便时再退 `fetch-x`。

## 安装 / 启用（给 Codex / 你自己）

1. 本 skill 目录已放好：`~/.agents/skills/superx/`
2. 推荐把 wrapper 放到 PATH：

```bash
chmod +x ~/.agents/skills/superx/scripts/superx.py
ln -sf ~/.agents/skills/superx/scripts/superx.py ~/.local/bin/superx
# 或全局
sudo ln -sf ~/.agents/skills/superx/scripts/superx.py /usr/local/bin/superx
```

3. 确保 `grok` CLI 可用且已登录（XAI_API_KEY 或 `grok login`）：

```bash
which grok
grok -p "hello" --yolo --max-turns 1 --output-format json | jq .
```

4. Grok 自己也会自动发现本 skill（如果你的 ~/.grok/config.toml 或 agent 加载了 .agents/skills 路径）。

## 使用（Codex / 脚本 / 命令行）

### 推荐：用 wrapper（输出干净 JSON）

```bash
# 1. 搜用户
superx user "xAI" --count 3

# 2. 语义搜索帖子
superx semantic "Grok 4.3 or new xAI model announcement" --limit 5 --from-date 2026-04-01

# 3. 高级关键词搜索（支持完整高级语法）
superx keyword 'from:xai OR from:grok since:2026-05-01 min_faves:200' --mode Latest --limit 8

# 4. 抓完整线程（支持 URL 或纯 ID）
superx thread 1661523610111193088
superx thread 'https://x.com/xai/status/1661523610111193088'

# 5. 抓 X long-form article / 长帖正文，并缓存为 Markdown
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20'
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --path-only
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --format json
superx article 'https://x.com/0xenderzcx/status/2061778310934516097?s=20' --cache-dir ./.superx
```

wrapper 内部构造严格 prompt，强制 Grok 只调用对应 `x_*` 工具，然后只吐 tool result 的 JSON。`article` 子命令会先尝试 Grok 原生 `x_thread_fetch`，不行再 fallback 到 `opencli twitter article -f json`，并默认保存 Markdown 缓存到当前项目 `./.superx/articles/`，避免重复抓同一篇长文。可用 `--cache-dir` 或 `SUPERX_CACHE_DIR` 改缓存根目录。

### 一次性调研 / research（解决 copy-paste 痛点）

这是 superx 专门为你这个习惯新增的核心能力。

**旧流程（低效）**：
Codex 出 prompt → 你复制粘贴到网页 Grok → 结果复制回来喂 Codex。

**新流程（一行命令，默认重度）**：
```bash
superx research "调研 2026 年本地 AI agent 如何更好使用 Grok Build 原生 X 工具 + web 调研 + research 缓存" --path-only
```

- 默认即重度专家模式：`--effort max --model grok-build --check --max-turns 10`（无需额外指定）。
- superx 直接调用**本地 grok** 做 one-shot research（会按需使用 web_search、open_page、原生 X 工具等）。
- 默认定位是 **X-first / frontier research**，不是通用 Grok 协作桥。
- 输出高质量结构化 Markdown（Executive Summary、Key Findings、Sources 等）。
- 自动保存到 `./.superx/research/<ts>-<slug>.md`，旁边写 metadata JSON。
- Codex 之后直接 `read_file .superx/research/xxx.md` 继续工作，完全零中转。
- 不支持 background job、status/result/cancel、follow-up session；这些留给未来 `grb` / Grok bridge。

**推荐在 Codex 长期指导里加入**（强烈建议）：
"需要对 X 相关、前沿工具链、AI agent 实践等主题做一次性调研时，**直接 shell 执行 `superx research \"详细问题\" --path-only`**（默认即重度专家模式：effort=max + check + model=grok-build + max-turns=10），不要再生成 prompt 让我手动去网页 Grok 粘贴。结果会自动落盘到 .superx/research/ 下，后续直接读本地文件。"

其他参数（用于微调，覆盖默认重度设置）：
```bash
superx research "topic" --max-turns 12          # 更深研究（默认10）
superx research "topic" --output ./notes.md     # 自定义输出
superx research "topic" --format json           # 拿缓存路径等元信息
superx research "topic" --path-only             # 只返回 Markdown 路径
superx research "topic" --timeout 1200          # 调整 Grok 超时
superx research "topic" --retries 2             # Grok 偶发空输出时重试
superx research "topic" --allow-partial         # 接受 Grok 非零退出后的 partial 报告

# 覆盖默认重度专家模式
superx research "topic" --effort high           # 降低到 high（默认 max）
superx research "topic" --no-check              # 关闭自检（默认开启）
superx research "topic" --model grok-composer-2.5-fast  # 换快模型
superx research "topic" --reasoning-effort high # 仅限支持的模型；grok-build 会 400
superx research "topic" --session-id 019e...    # 恢复已有 Grok session id（来自 `grok sessions list`，不能创建自定义名）
```

这些参数会直接透传给本地 grok CLI。
`--check`（默认开）会消耗更多 turns，建议默认 `--max-turns 10` 起；如需更狠可手动 `--max-turns 12`。
`--session-id` 只能恢复真实已有 session，不会创建自定义命名 session。
当前本机 `grok models` 可见 `grok-build`（默认，重度推荐）和 `grok-composer-2.5-fast`；`grok-build` 不支持 `--reasoning-effort`，传了会 400。

`--retries` 只处理“没有可保存 Markdown”的情况，不是账号权限、rate limit 或无会员 fallback。

它把本地 grok 变成了 Codex 的一次性研究后端；持续协作另做 `grb`，不要把 superx 泛化成持续协作桥。

### 直接用 grok CLI（无需 wrapper，适合一次性的）

```bash
# 用户搜索
grok -p 'You MUST call x_user_search with query="xAI" count=3. After result, output ONLY the tool JSON result, nothing else.' --yolo --output-format json | jq -r '.text'

# 语义
grok -p 'MUST use x_semantic_search. query="xAI Grok release notes" limit=5 from_date="2026-04-01". Output ONLY tool result JSON.' --yolo --output-format json | jq -r '.text'

# 关键词（高级语法全支持）
grok -p 'Call x_keyword_search. query="from:xai min_faves:100 since:2026-05-01", mode="Latest", limit=10. ONLY the tool JSON.' --yolo --output-format json | jq -r '.text'

# 线程
grok -p 'Use x_thread_fetch with post_id="1661523610111193088". Output ONLY the full thread JSON from the tool.' --yolo --output-format json | jq -r '.text'
```

## 参数速查（对应原生工具 schema）

- **user**: `query` (必), `count` (1-10, 默认3)
- **semantic**: `query` (必), `limit`, `from_date`, `to_date`, `min_score_threshold`
- **keyword**: `query` (必，高级语法), `limit`, `mode` ("Latest"|"Top"), `from_date`, `to_date` ...
- **thread**: `post_id` (数字字符串或可从中抽取的 URL)
- **article**: `source` (status/article URL 或 ID), `--format md|json`, `--path-only`, `--force`, `--output`, `--cache-dir`, `--source-mode auto|grok|opencli`
- **research**: `query` (必), `--max-turns`, `--format md|json`, `--path-only`, `--timeout`, `--retries`, `--allow-partial`, `--output`, `--cache-dir`, `--model` (default grok-build), `--effort` (default max), `--reasoning-effort`, `--session-id`, `--no-check` (默认开启自检)

更多过滤见原生工具定义（from_date 等对 keyword/semantic 都有效）。

## 集成到 Codex（或其他 agent）

- **X 结构化搜索**：直接 `superx user / semantic / keyword / thread / article`，拿 JSON。
- **一次性深度研究**：`superx research "问题" --path-only`（默认重度专家模式：effort=max + check + model=grok-build + max-turns=10），拿 Markdown + metadata 缓存。**这是解决你主要痛点的推荐方式**。
- 覆盖默认：用 `--no-check` 关闭自检、`--effort high` 降级、`--max-turns 12` 更深、`--session-id <真实id>` 跟进（只能恢复 `grok sessions list` 里的，不能创建自定义名）。
- 在 Codex 的系统 prompt / task 开头或 AGENTS.md 里明确指导：
  > 当需要调研 X 内容、前沿工具链或 AI agent 实践时，**直接 `superx research \"...\" --path-only`**（默认就是重度专家模式），不要再生成 prompt 让我手动去网页 Grok 粘贴。结果自动落 .superx/research/，后续直接读文件。
- 如果要像 `crb` 一样支持 background/status/result/follow-up，应新做 `grb` / Grok bridge，而不是继续扩 superx。

更新 wrapper 后，记得 `chmod +x` 并测试。

## 适用范围 / 何时禁用

**适用**：
- 需要结构化 X 用户/帖子数据（ID、粉丝、metrics、replies 树）。
- 高级过滤 + 语义混合查询。
- 需要抓 X long-form article / 长帖正文，并落成可复用 Markdown 文件。
- 需要对 X 相关、前沿工具链、AI agent 实践等主题做一次性调研（web + X + 其他），并希望结果自动缓存为本地 Markdown，去掉网页 Grok 的 copy-paste 中转（默认即重度专家模式）。
- 想用类似网页专家模式的 effort/model/check（默认重度）或用真实 Grok session id 做有限 follow-up。
- Codex / 本地 agent 想复用 Grok 的一次性研究能力（尤其是原生 X 工具）。
- 避免 Chrome/extension 冲突（fetch-x 的常见痛点）。

**何时禁用 / 退回 fetch-x**：
- 只需要抓**已知单条普通 URL 的正文 + replies**，且不需要 Grok metrics/schema（fetch-x/opencli 可能更轻）。
- 没有 grok CLI / 没登录 XAI_API_KEY 的环境。
- 想抓 X-native long article 但本机没有 `opencli` fallback，或 Chrome/opencli 未配置。
- 需要 background/status/result/cancel 或可管理的连续协作能力（未来 `grb` 负责）。
- 纯公开网页抓取（用 Waza read 或 web tools）。

## 故障排查

- `grok: command not found` → `export PATH="$HOME/.local/bin:$PATH"` 或用全路径。
- 工具没返回 / 乱输出 → wrapper 里的 prompt 已经很严格；可加 `--max-turns 5` 重试，或直接在 grok TUI 里先验证 `x_user_search` 等。
- 认证问题 → `grok login` 或 `export XAI_API_KEY=...`
- 某些高级语法不生效 → 确认 query 字符串正确（Grok 会原样传给工具）。
- jq 没装 → wrapper 仍会打印 text，Codex 自己 parse 即可。

## 维护

- 本 skill 位置：`~/.agents/skills/superx/`
- wrapper 源码：`scripts/superx.py`（X 工具用严格 force prompt；research 用 one-shot agent prompt + 缓存）
- X 专用子命令保持结构化 JSON；`research` 子命令默认重度专家模式（effort=max + check + model=grok-build + max-turns=10），并支持 --effort/--model/--session-id 等覆盖接近网页专家模式。
- 更新 wrapper 后 `chmod +x` 并重测。

**直接结论**：
- X 搜索/线程/article：`superx xxx` 一行出结构化数据 + 缓存。
- 一次性深度调研：`superx research "..." --path-only`（**默认重度**：effort=max + check + model=grok-build + max-turns=10）—— 直接解决你之前 "Codex 出 prompt → 网页 Grok → 复制回来" 的循环。本地 grok 做 one-shot research，结果落盘 .superx/research/，Codex 直接读文件。
- 用 `--no-check` / `--effort high` / `--max-turns 12` / `--session-id <真实id>` 等微调（session 只能恢复已有，不能自定义名；grok-build 不支持 reasoning-effort）。

需要扩展更多（follow-up session 支持、MCP 包装、research 模板参数等），随时说。
