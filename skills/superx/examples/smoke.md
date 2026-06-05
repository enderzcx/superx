# superx Smoke Examples

Use these examples to verify the wrapper surface without making claims about X data freshness.

## Help Surface

```bash
superx --help
```

Expected: exits `0` and lists `user`, `semantic`, `keyword`, `thread`, `article`, and `research`.

## Article Path Cache

```bash
superx article "https://x.com/<user>/status/<id>" --path-only
```

Expected: prints a local Markdown path under `.superx/articles/`.

## Research Cache

```bash
superx research "AI agent workflow examples on X" --path-only
```

Expected: prints a local Markdown path under `.superx/research/`.

Do not use these examples as proof that Grok-native X tools are available. If auth or membership is missing, report the capability gap and use documented fallback routes.
