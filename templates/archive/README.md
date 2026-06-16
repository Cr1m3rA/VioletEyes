# templates/archive/

This directory holds retired versions of templates that have been
superseded. They are kept for reference and historical diffing.

| File | Status |
|---|---|
| `report.html.v1` | Single-file hand-written HTML + CSS from the original report renderer (v1.0). Superseded by the Jinja2 templates under `templates/` (root) and `templates/partials/`. |

If you need to roll back to the v1 renderer, see
`scripts/archive_render_report.py` for the matching Python script.