# Open research tagging

Rebuild of the open-research-tagging demo: code OSS AI contribution policies via GitHub PR review comments, then browse them on a static site.

How the pieces fit together (kept up to date as we build): [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Setup (dev)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Draft-codebook tag-check policy

While the codebook is still changing, `python -m open_research_tagging.check_tags` **hard-fails the PR check only on malformed tags** (e.g. bare `#Design`, unparseable `#…`). Well-formed but unknown ids (e.g. `#stance/not-in-codebook-yet`) are still reported (and can get a reply / `needs_tag_review` on the site) but do **not** fail the status check. Use `--soft` to always exit 0.

## Local site preview

```bash
cd site && python3 -m http.server 8000
```

Open http://localhost:8000/ (comments) or http://localhost:8000/projects.html. Shared CSS/JS live under `site/css/` and `site/js/`; filter dimensions come from `data/codebook.json`.
