# v1 compatibility

Read this reference only when an existing Markdown report or an explicit v1
request must be rendered. The stable entrypoint remains:

```bash
node /path/to/skill/scripts/render_html.mjs \
  --report "<report.md>" \
  --metadata "<metadata.json>" \
  --out "<report.html>"
```

The reader-facing sections remain `內容重述` → `洞見` → `food for thoughts` →
`可行啟發`. Legacy `驗證與限制` material is discarded by the renderer rather
than copied into HTML. Lists in insight, reflection, and action sections are
flat unordered lists. v1 does not gain v2 evidence semantics; use the v2 spec
and finalizer for new reports.
