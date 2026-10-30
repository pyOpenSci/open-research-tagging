# Architecture

How open-research-tagging fits together: pipeline, static site, coder helpers, and GitHub Actions.

## Contents

- [What this system is](#what-this-system-is)
- [Mental model](#mental-model)
- [End-to-end data flow](#end-to-end-data-flow)
- [Codebook](#codebook)
- [Passage tags](#passage-tags)
- [Comments → `comments.json`](#comments--commentsjson)
- [Projects → `projects.json`](#projects--projectsjson)
- [Static site](#static-site)
- [Coder helpers](#coder-helpers)
- [Emit drift](#emit-drift)
- [GitHub Actions](#github-actions)
- [Fixture vs live site JSON](#fixture-vs-live-site-json)
- [How we keep this document current](#how-we-keep-this-document-current)
- [Reference: module map](#reference-module-map)
- [Reference: still ahead (Phase 12+)](#reference-still-ahead-phase-12)

## What this system is

Researchers study how open-source projects treat AI-generated contributions. Policy text lives under `projects/<slug>/`. Coders leave **PR review comments** (Files tab) with codebook hashtags. Maintainer/Actions scripts turn those comments into JSON; a **static** site lets people browse and filter them.

GitHub is the editor. The site is read-only. There is no app server.

## Mental model

Two kinds of judgment, stored in different places:

| Layer | Where | Question it answers |
|-------|--------|---------------------|
| **Overall** | `projects/<slug>/project.yaml` (`coding:` block) | How do we code this policy as a whole? |
| **Passage** | Hashtags on PR review comments | What does this line or paragraph evidence? |

The **codebook** (`codebook/codebook.yaml`, draft-0.2) is the shared vocabulary: stable string **ids** for codes, human **labels** for display. Each research dimension has **Explicit** (stated in policy docs) and **Implicit** (practices / signals) subsections. Passage hashtags and projects-page filters target Explicit leaves for now; Implicit is set on the coding view / `project.yaml`. The browser gets generated `site/data/codebook.json` so there is not a second hand-edited codebook. When the YAML shape changes, see [`codebook/EVOLUTION-NOTES.md`](../codebook/EVOLUTION-NOTES.md) for what else usually needs a hand update.

## End-to-end data flow

```text
projects/<slug>/ + project.yaml     codebook.yaml
        |                                |
        |                         emit codebook.json
        |                                |
GitHub PR Files (#tags)                  |
        |                                |
        v fetch                          |
   raw_comments.json                     |
        |                                |
        v process_comments <-------------+
   comments.json
        |
        v process_projects
   projects.json
        |
   projects.html <---> index.html
         |                  |
    tags.html          coding.html
    (stage hashtags    (form → copy coding: YAML
     → paste on PR)     → paste into project.yaml)
```

## Codebook

- Load and validate YAML shape (required fields, unique ids within each list).
- Index for lookups by dimension, namespace, and value id (`Codebook` in `codebook.py`).
- Emit browser JSON (`codebook_emit.py` / `emit_codebook` CLI → `site/data/codebook.json`), including a **`tag_catalog`** of every valid hashtag string and a **`coding_schema`** (dimension → Explicit/Implicit → fields) that drives the coding-view form and `empty_coding()` defaults.
- YAML `namespaces` map hashtag namespaces (e.g. `rationale`) to dimension ids (e.g. `stated_rationale`), including optional `path` for nested leaves.

While the codebook is still a draft, CI **hard-fails only on malformed tags** (see [Tag-check](#tag-check)); unknown-but-well-formed ids stay soft.

## Passage tags

Pipeline for a comment body:

1. **Parse** — `#namespace/value`, `#namespace:value` (colon slip), and `#scope/type:position`.
2. **Enrich** — attach dimension, labels, `display`, and `filter_key` from the codebook. Unknown values still get a humanized fallback label so nothing disappears silently.
3. **Warn** — bare `#Word` tokens, unknown namespaces/values, bad scope type/position. Any warnings set `needs_tag_review` on the normalized row.

## Comments → `comments.json`

### Provenance (refs)

From a raw GitHub review-comment object:

- **project** — first folder under `projects/`, or none for `_template` / paths outside `projects/`
- **pr_number**, **user**, **html_url**, **path**

### Quotes (passage preview)

1. If the file still exists in the workspace, read it. Multi-line comments use those exact lines; a single-line comment expands to the surrounding paragraph (until blank lines).
2. If the file is missing, clean GitHub’s `diff_hunk` (drop patch headers and pure deletions).
3. If neither works, store no quote; the comment can still exist without a preview.

### Normalize

`normalize` combines refs, tags, warnings, and quote into one site row. Malformed or unknown tags stay on the row with `parse_warnings` and `needs_tag_review: true` — nothing is dropped. `process_comments` **skips** review comments whose login ends in `[bot]` (e.g. tag-check replies from `github-actions[bot]`), so bot text that quotes bad hashtags does not become research evidence.

```bash
python -m open_research_tagging.process_comments \
  --in site/data/raw_comments.json --out site/data/comments.json
```

Output shape: `{ meta, data }`. Meta includes `source_file`, `count`, `is_fixture` (true when the input filename contains `fixture`), and `codebook_version`. Raw input is a JSON list or `{ "comments": [...] }`; already-processed `{ meta, data }` is rejected.

## Projects → `projects.json`

Each studied policy lives under `projects/<slug>/` with a `project.yaml` (provenance, overall `coding:`, `files:`). Copy `projects/_template/` to start a new slug. Discovery skips folder names starting with `_`. The development seed is **pyOpenSci** (`projects/pyopensci/`). If `display_name` is still the template placeholder `Example Project`, site rows use the **slug** instead (**13g**); the YAML file is left unchanged until a coder edits it.

**Provenance (13f):** only `source_repo`, `source_commit`, `source_url`, `retrieved_at`, and `notes`. `source_url` is optional (null when there is no single primary policy URL); pin the snapshot with repo + commit instead. Policy location / date live under `coding.context` when coded; retired top-level provenance keys are dropped on normalize / Copy YAML. Each `files:` entry is `path` plus optional `description` and `notes`.

Joining overall codes to passage evidence:

1. Index normalized comments per project (by dimension and `filter_key`).
2. Read that project’s `coding:` block from `project.yaml`.
3. For each overall code, attach codebook labels and links into the comment browser (“all on this dimension” / “exact code”).

Practical details: scope `not_addressed` is omitted from the sparse table; unknown overall ids still show and are flagged; YAML scope keys may use underscores while hashtags use hyphens — matching normalizes that. The YAML→site field map is an explicit adapter for the known nesting (not a generic “any codebook dimension → form” engine). For draft-0.2, `build_overall` flattens each dimension’s **Explicit** subsection into the projects-table chips; Implicit stays on the nested `coding` passthrough for the coding view.

**Open PRs (13a):** review comments already refresh from every PR. Project rows normally come from `projects/` on the branch Actions checked out (main). Deploy/refresh jobs run `process_projects --include-open-prs`, which also loads `projects/*/project.yaml` from **open** PRs at each PR head and merges those rows when the slug is not already on main (main wins on conflict). Open-PR rows carry `from_open_pr` / `pr_number`. Local/fixture regen leaves the flag off so it stays offline.

```bash
python -m open_research_tagging.process_projects \
  --comments site/data/comments.json --out site/data/projects.json
# Actions refresh also passes --include-open-prs (needs GITHUB_TOKEN + repo).
```

Each row carries processed `overall` (projects table) and raw nested `coding` (coding-view pre-fill). YAML 1.1 bare `yes`/`no` normalize to string ids so JSON does not store booleans. Missing comments file → empty index and a warning (project rows still emit).

## Static site

Shared chrome under `site/` (Alpine.js + DataTables from CDN). Local preview: `cd site && python3 -m http.server 8000` → http://localhost:8000/

| Page | Role |
|------|------|
| `index.html` | Comment browser (filters, quotes, deep links) |
| `projects.html` | Overall codes + evidence links into the browser |
| `tags.html` | Passage **tag picker** (search / stage / Copy hashtags) |
| `coding.html?project=<slug>` | Overall **coding view** (evidence + metadata + schema form + Copy full `project.yaml`) |

**Comment browser URL params** (same shapes the projects join emits):

| Param | Effect |
| --- | --- |
| `project` | Restrict to that project slug |
| `dimension` | Any comment tagged on that dimension |
| `filter` | Exact `filter_key` (e.g. `stance:allow` or `scope:code:restricted`) |
| `scope_type` / `scope_position` | Scope match (full pair or partial) |
| `needs_tag_review=1` | Only rows flagged for tag review |

Also in-page: text search, project/PR selects, dimension chips, Clear. Fixture banner when `comments.json` `meta.is_fixture` is true.

Browse / helper regression: Playwright tests under `tests/test_site_integration.py`, `test_tag_picker_paste.py`, `test_coding_walkthrough.py` (need `playwright install chromium` and network for CDNs). They serve a **temp** copy of `site/` filled from the offline fixture — see [Fixture vs live](#fixture-vs-live-site-json).

## Coder helpers

Documented for researchers in [`codebook/COMMENTING.md`](../codebook/COMMENTING.md) and the PR template.

| Need | Tool |
|------|------|
| Tag a **passage** | Tag picker → Copy → Files-tab review comment (hashtags at top, then a short note). Prefer **Add single comment** or **Submit** the review — unsubmitted “Start a review” drafts often cannot receive bot replies. |
| Set **overall** codes / metadata | Coding view → walk evidence → edit provenance → **Copy YAML** → paste over whole `project.yaml` (files list read-only). Do not invent overall YAML by pasting random hashtags into the file. |

Exact hashtag strings come from the picker / `tag_catalog`, not a second hand-maintained table in the docs.

## Emit drift

Tag picker copy-text and coding-view **Copy YAML** run in the browser; canonical strings and YAML shape are defined and tested in **Python** (`tag_catalog.py`, `coding_yaml.py`, `project_yaml.py`). Two implementations can drift.

**v1 approach:** Python goldens / helpers are the contract; Playwright paste/preview tests check the browser against that contract. Do not invent a third source of truth or a shared JS/Python runtime unless drift becomes chronic.

## GitHub Actions

| Workflow | When | What |
|----------|------|------|
| `test.yml` | Push to `main`, PRs | `pytest` (incl. Playwright) |
| `check-comment-tags.yml` | Review comment create/edit; PR open/sync | Soft reply on bad tags; PR scan hard-fails **malformed** only |
| `update-comments.yml` | Daily cron + manual | Fetch → process → emit codebook → process projects (incl. open PRs) → **deploy Pages artifact** (no git commit) |
| `deploy-pages.yml` | Push touching `site/` / `projects/` / `codebook/` / package, or manual | Same rebuild + deploy (no git commit) |

**Org production Pages:** https://www.pyopensci.org/open-research-tagging/  
**Personal/test staging (optional):** https://shaunagm.github.io/open-research-tagging/

### Tag-check

```bash
python -m open_research_tagging.check_tags --from-event --reply --soft
python -m open_research_tagging.check_tags --pr N
```

- **Reply job** (`--soft`): always green; posts a bot reply when tags look wrong.
- **Scan job**: fails the PR check only on **malformed** tags while the codebook is draft. Well-formed unknown ids are reported (and may get a reply / `needs_tag_review` after refresh) but do not fail the check.
- Checkout uses the **default branch** (not the PR head) so content PRs that lag `main` still run the published checker. Note: `pull_request_review_comment` still **selects the workflow YAML** from the PR merge ref — a PR opened before a workflow fix must update its branch (merge/rebase `main`) once to pick up new workflow files.
- Replies require a **submitted**, top-level review comment (see COMMENTING.md).

### Fetch and refresh quirks

```bash
python -m open_research_tagging.fetch_comments   # needs GITHUB_TOKEN / GITHUB_REPOSITORY
```

Writes gitignored `site/data/raw_comments.json`. Live `comments.json` / `projects.json` / `codebook.json` are built **in the Actions runner** and uploaded as the Pages artifact only (**13c**) — they are **not** committed back to `main`. That removes bot refresh commits racing human pushes. Committed `site/data/*.json` on `main` is the **offline fixture snapshot** for local `http.server` and clones without a token.

No `paths:` filter on tag-check yet; revisit if code-review `#…` noise on non-`projects/` PRs becomes a problem.

## Fixture vs live site JSON

| | Offline fixture (committed / Playwright) | Live (public Pages) |
|--|-----------------|--------------------------------------|
| Raw input | `site/data/raw_comments.fixture.json` | Fetched PR review comments in Actions |
| After process | `is_fixture: true`, dense demo/pyOpenSci tags | `is_fixture: false`, whatever is tagged on this remote |
| Consumers | Playwright temp site; local `site/` preview; git clone | Pages artifact only (not on `main`) |

**Update comment data** / **Deploy Pages** regenerate live JSON in CI and deploy — the public site shows GitHub data; `main` keeps the fixture snapshot until a human regenerates it from the fixture on purpose. Playwright copies `site/` into a **temp directory**, regenerates fixture-shaped JSON there, and serves that tree (`site_under_test` / `site_base_url` in `tests/conftest.py`).

With `projects/pyopensci/` present, fixture quotes usually resolve from local policy files (`paragraph` / `selection`) instead of `diff_hunk`.

## How we keep this document current

- When a plan task changes how pieces fit together, update the matching section here in the same handoff (small diffs).
- Prefer extending this file over replacing it with a from-scratch draft at the end of a phase.

## Reference: module map

*Skippable inventory — package root `src/open_research_tagging/`.*

| Module | Role |
|--------|------|
| `codebook.py` | Validate, load, index codebook YAML |
| `codebook_emit.py` | Write `site/data/codebook.json` (includes `tag_catalog`) |
| `emit_codebook.py` | Maintainer/Actions CLI → `codebook.json` |
| `tag_catalog.py` | Canonical hashtag list for the tag picker |
| `coding_yaml.py` | Emit paste-ready `coding:` YAML (coding-view Copy) |
| `tags.py` | Parse, enrich, warn on hashtags |
| `comments.py` | Refs, `normalize`, load/write `comments.json` |
| `quotes.py` | Local file or diff_hunk quote resolution |
| `process_comments.py` | Maintainer/Actions CLI for normalize + write |
| `projects.py` | Discover/load YAML; comment index; build rows |
| `process_projects.py` | Maintainer/Actions CLI for `projects.json` |
| `github_client.py` | Shared GET/POST + Link pagination (injectable for tests) |
| `fetch_comments.py` | Maintainer/Actions CLI → `raw_comments.json` |
| `check_tags.py` | Tag-check library + Actions CLI |

Site JS (under `site/js/`): `codebook.js`, `chips.js`, `comments_filters.js`, `comments.js`, `projects_filters.js`, `projects.js`, `tags_stage.js`, `tags.js`, `coding_resolve.js`, `coding_form.js`, `coding.js`.

## Reference: still ahead (Phase 12+)

*Skippable checklist — detail lands in main sections when each task ships.*

- Codebook content swap (**12e**); seed retire when ready (**12f**); org Pages cutover (**12g**)
- Optional Tests CI Playwright install speedup (**12h**)
- Optional mutation spot-check (plan **Maybe later**, not Phase 13)
- Optional README screengrab GIFs (deferred; see plan open questions)
