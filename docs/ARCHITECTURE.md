# Architecture

How open-research-tagging fits together.

**Status:** describes what exists through fetching raw review comments (plan tasks through 6b). Tag-check CLI, the static site UI, and CI workflows are not built yet.

## What this system is

Researchers study how open-source projects treat AI-generated contributions. Policy text is copied into this repository under `projects/<slug>/`. Coders leave **PR review comments** on those files, using codebook hashtags. Scripts will turn those comments into JSON; a static site will let people browse and filter them.

GitHub is the editor. The site is read-only. There is no app server.

## Mental model

Two kinds of judgment, stored in different places:

| Layer | Where | Question it answers |
|-------|--------|---------------------|
| **Overall** | `projects/<slug>/project.yaml` | How do we code this policy as a whole? |
| **Passage** | Hashtags on PR review comments | What does this line or paragraph evidence? |

The **codebook** (`codebook/codebook.yaml`) is the shared vocabulary: stable string **ids** for codes, human **labels** for display. The browser gets a generated `site/data/codebook.json` so we do not maintain two hand-edited codebooks.

## What’s built so far

### Codebook

- Load and validate YAML shape (required fields, unique ids within each list).
- Index for lookups by dimension, namespace, and value id (`Codebook` in `codebook.py`).
- Emit browser JSON (`codebook_emit.py` → `site/data/codebook.json`).
- `namespaces` in the YAML map hashtag namespaces (e.g. `rationale`) to dimension ids (e.g. `stated_rationale`), including optional `path` for nested leaves.

### Tags on comments

Pipeline for a comment body:

1. **Parse** — find `#namespace/value`, `#namespace:value` (colon slip), and `#scope/type:position`.
2. **Enrich** — attach dimension, labels, `display`, and `filter_key` from the codebook. Unknown values still get a humanized fallback label so nothing disappears silently.
3. **Warn** — bare `#Word` tokens, unknown namespaces/values, bad scope type/position. Any warnings set `needs_tag_review` on the normalized row.

### Comment provenance (refs)

From a raw GitHub review-comment object we derive:

- **project** — first folder under `projects/`, or none for `_template` / paths outside `projects/`
- **pr_number**, **user**, **html_url**, **path**

### Quotes (passage preview)

For the UI excerpt of what was tagged:

1. If the file still exists in the workspace, read it. Multi-line comments use those exact lines; a single-line comment expands to the surrounding paragraph (until blank lines).
2. If the file is missing, clean GitHub’s `diff_hunk` (drop patch headers and pure deletions).
3. If neither works, store no quote; the comment can still exist without a preview.

### Normalize → `comments.json`

`normalize` combines refs, tags, warnings, and quote into one site row. Malformed or unknown tags stay on the row with `parse_warnings` and `needs_tag_review: true` — nothing is dropped.

Maintainers / Actions run:

```bash
python -m open_research_tagging.process_comments --in site/data/raw_comments.json --out site/data/comments.json
```

Output shape: `{ meta, data }`. Meta includes `source_file`, `count`, `is_fixture` (true when the input filename contains `fixture`), and `codebook_version`. Raw input is a JSON list or `{ "comments": [...] }`; already-processed `{ meta, data }` is rejected.

**Offline path:** `site/data/raw_comments.fixture.json` is a committed dump of demo-shaped review comments (no network). Regenerating with `process_comments` writes committed `site/data/comments.json` so the site and CI can run without a GitHub token. Live fetch will write gitignored `raw_comments.json` later; the fixture stays the deterministic stand-in. With `projects/pyopensci/` present, fixture quotes usually resolve from local policy files (`paragraph` / `selection`) instead of `diff_hunk`.

### Projects on disk

Each studied policy lives under `projects/<slug>/` with a `project.yaml` (provenance, overall `coding:`, `files:`). Copy `projects/_template/` to start a new slug. Discovery skips any slug whose folder name starts with `_`, so `_template` never becomes a `projects.json` row. The first real seed is **pyOpenSci** (`projects/pyopensci/`): policy markdown plus a filled `project.yaml`, joined with the comment fixture into committed `site/data/projects.json`.

**Putting overall codes next to passage evidence**

Remember the two layers: **overall** codes live in `project.yaml` (how we code the policy as a whole); **passage** tags live on PR comments (evidence on specific lines).

For the projects page we need both in one place. The pipeline:

1. Look through all normalized comments and, for each project, remember which comment ids mention which dimension or specific code (the comment index).
2. Read that project’s `coding:` block from `project.yaml`.
3. For each overall code, attach human labels from the codebook and links into the comment browser — “all comments on this dimension” and “comments that match this exact code.”

A few practical details: scope entries marked `not_addressed` are skipped so the table stays sparse; if `project.yaml` uses an id the current codebook doesn’t know, we still show it and flag it for review rather than dropping it. Scope keys in YAML sometimes use underscores (`docs_and_text`) while hashtags use hyphens (`docs-and-text`); we normalize that when matching. The mapping from YAML fields to site fields is hand-written for the known layout — we are not auto-generating it from every codebook dimension.

Maintainers / Actions emit the joined file with:

```bash
python -m open_research_tagging.process_projects --comments site/data/comments.json --out site/data/projects.json
```

Output shape: `{ meta, data }` with `count`, `comments_source`, and `codebook_version`. Missing comments file → empty index and a warning (project rows still emit).

## Module map

| Module | Role |
|--------|------|
| `codebook.py` | Validate, load, index codebook YAML |
| `codebook_emit.py` | Write `site/data/codebook.json` |
| `tags.py` | Parse, enrich, warn on hashtags; group codes by dimension |
| `comments.py` | Refs, `normalize`, load/write `comments.json` payload |
| `quotes.py` | Local file or diff_hunk quote resolution |
| `process_comments.py` | Maintainer/Actions CLI for normalize + write |
| `projects.py` | Discover/load YAML; comment index; build rows; write payload |
| `process_projects.py` | Maintainer/Actions CLI for `projects.json` |
| `github_client.py` | Shared GET + Link pagination (injectable for tests) |
| `fetch_comments.py` | Maintainer/Actions CLI → `raw_comments.json` |

Package root: `src/open_research_tagging/`.

### GitHub HTTP (shared)

`github_client` builds auth headers and GETs JSON from the GitHub API, following `Link: rel="next"` for pagination. Fetch and tag-check share this module. Tests inject a `getter` (or stub `urlopen`) so CI never calls the live API. Stdlib only for v1; a fuller client (e.g. PyGithub) can replace this later if the thin wrapper stops being enough.

**Fetch:** maintainers / Actions run:

```bash
python -m open_research_tagging.fetch_comments --owner ORG --repo NAME
# or set GITHUB_REPOSITORY=owner/repo (and optional GITHUB_TOKEN)
```

Writes gitignored `site/data/raw_comments.json` (`{ source, endpoint, count, comments }`). Offline work keeps using `raw_comments.fixture.json` instead.

## How we keep this document current

- When a plan task changes how pieces fit together, update the matching section here in the same handoff (small diffs).
- Do not wait for a final “docs phase” to explain new behavior.
- Later polish (full site, Actions, coder helpers) extends this file; it should not replace it with a first draft from scratch.

## Not built yet

*Skippable checklist of upcoming pieces — detail will land here when those tasks ship.*

- Tag-check entrypoint for Actions (reply / PR scan)
- Static site (browse / tag picker / coding view)
- GitHub Actions (tests, tag check, Pages refresh)
