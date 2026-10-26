# Open research tagging

Rebuild of the open-research-tagging demo: code OSS AI contribution policies via GitHub PR review comments, then browse them on a static site.

How the pieces fit together (kept up to date as we build): [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Setup (dev)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium   # once; needed for site integration tests
pytest
```

## CI

On push to `main` and on pull requests, GitHub Actions runs `pytest` (including Playwright site tests). Locally: `pip install -e ".[dev]"`, `playwright install chromium`, then `pytest`.

**Check comment tags** (`.github/workflows/check-comment-tags.yml`): replies on Files-tab review comments with tag issues; PR status check scans all review comments. See draft policy below.

**Update comment data** (`.github/workflows/update-comments.yml`): daily + manual dispatch — fetch review comments, reprocess site JSON (including `codebook.json`), commit, and deploy Pages in one job.

**Deploy Pages** (`.github/workflows/deploy-pages.yml`): publishes `site/` when `site/**` changes on `main`, or via manual dispatch. Requires Pages source = GitHub Actions (Phase **11f**).

## Draft-codebook tag-check policy

While the codebook is still changing, `python -m open_research_tagging.check_tags` **hard-fails the PR check only on malformed tags** (e.g. bare `#Design`, unparseable `#…`). Well-formed but unknown ids (e.g. `#stance/not-in-codebook-yet`) are still reported (and can get a reply / `needs_tag_review` on the site) but do **not** fail the status check. Use `--soft` to always exit 0.

## Local site preview

```bash
cd site && python3 -m http.server 8000
```

Open http://localhost:8000/ for the comment browser, http://localhost:8000/projects.html for overall codes, http://localhost:8000/tags.html for the **tag picker** (stage/copy hashtags for GitHub review comments), or http://localhost:8000/coding.html?project=pyopensci for the **coding view** (overall codes + evidence → Copy YAML). See [`codebook/COMMENTING.md`](codebook/COMMENTING.md) for when to use each.

## Enable GitHub Pages / demo prep

One-time on the GitHub remote (personal/test host first; org cutover later):

1. **Settings → Pages → Build and deployment → Source:** GitHub Actions.
2. Push workflows on `main` (or merge a PR that adds `.github/workflows/`).
3. Run **Actions → Update comment data → Run workflow** once (or wait for the daily cron) so live comments refresh into `site/data/`.
4. Open the Pages URL and smoke-check: comments browser, projects overview, **tag picker**, **coding view** (`coding.html?project=<slug>`).
5. Record the public URL here when known: *(set in Phase 11f)*.

**Coder path:** tag picker → paste on Files-tab review comments → refresh site data → coding view → Copy YAML into `project.yaml`. PR checklist: [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).
