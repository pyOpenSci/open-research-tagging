# Architecture

How open-research-tagging fits together.

**Status:** describes what exists through the comment index for evidence links (plan tasks through 5b). Overall join into `projects.json`, fetch, the static site UI, and CI are not built yet.

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

**Offline path:** `site/data/raw_comments.fixture.json` is a committed dump of demo-shaped review comments (no network). Regenerating with `process_comments` writes committed `site/data/comments.json` so the site and CI can run without a GitHub token. Live fetch will write gitignored `raw_comments.json` later; the fixture stays the deterministic stand-in. Until `projects/pyopensci/` is seeded, quotes for those paths often come from `diff_hunk` rather than local files.

### Projects on disk

Each studied policy lives under `projects/<slug>/` with a `project.yaml` (provenance, overall `coding:`, `files:`). Copy `projects/_template/` to start a new slug. Discovery skips any slug whose folder name starts with `_`, so `_template` never becomes a `projects.json` row.

**Comment index:** from normalized `comments.json` rows, `comment_index` groups comment ids per project (`all_ids`, `by_dimension`, `by_filter_key`) so overall codes can link to matching passage evidence. `normalize_scope_key` maps YAML underscore keys (`docs_and_text`) to hashtag hyphen form (`docs-and-text`) until the template and codebook spellings are unified.

## Module map

| Module | Role |
|--------|------|
| `codebook.py` | Validate, load, index codebook YAML |
| `codebook_emit.py` | Write `site/data/codebook.json` |
| `tags.py` | Parse, enrich, warn on hashtags; group codes by dimension |
| `comments.py` | Refs, `normalize`, load/write `comments.json` payload |
| `quotes.py` | Local file or diff_hunk quote resolution |
| `process_comments.py` | Maintainer/Actions CLI for normalize + write |
| `projects.py` | Discover/load `project.yaml`; comment index + scope-key shim |

Package root: `src/open_research_tagging/`.

## How we keep this document current

- When a plan task changes how pieces fit together, update the matching section here in the same handoff (small diffs).
- Do not wait for a final “docs phase” to explain new behavior.
- Later polish (full site, Actions, coder helpers) extends this file; it should not replace it with a first draft from scratch.

## Not built yet

*Skippable checklist of upcoming pieces — detail will land here when those tasks ship.*

- Joining overall `project.yaml` codes to comment evidence (`projects.json`)
- Fetching review comments from the GitHub API
- Static site (browse / tag picker / coding view)
- GitHub Actions (tests, tag check, Pages refresh)
