# scripts/archive_render_report.py

This is the **v1.0** report renderer, kept for archival reference. It used
string-template `template.replace(k, v)` over a hand-written HTML file
(`templates/archive/report.html.v1`).

The current renderer is `scripts/render_report.py`, which uses Jinja2
templates under `templates/` and inlines Tailwind v4 / Alpine.js /
Chart.js / Mermaid.js / Prism.js for a fully-offline single-file output.

The two renderers accept the same CLI flags (`--findings`, `--assets`,
`--profile`, `--execution-log`, `--output`, `--project-name`,
`--target`, `--mode`, `--severity-floor`, `--partial`,
`--snippet-mode`, `--test-date-start`, `--test-date-end`).

If you need to compare outputs or roll back:

```bash
# v1.1 (current)
python scripts/render_report.py \
    --findings findings.json \
    --assets assets.json \
    --profile framework_profile.json \
    --execution-log execution.log \
    --output code-audit-report.html

# v1.0 (legacy)
python scripts/archive_render_report.py \
    --findings findings.json \
    --assets assets.json \
    --profile framework_profile.json \
    --execution-log execution.log \
    --report-template templates/archive/report.html.v1 \
    --output code-audit-report-legacy.html
```