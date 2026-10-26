# Codebook update touchpoints

When `codebook/codebook.yaml` changes, what else needs attention? Goal: content-only edits (new ids, new text fields under an existing leaf) should need **edit YAML → re-emit → reprocess**, not hand edits to the coding form.

Tracked as plan task **12f** (schema-driven coding view).

## After 12f — ordinary content edits

| Action | Need to hand-edit? |
|--------|-------------------|
| Add/rename label on an existing value id | No — re-emit |
| Add a new value id under an existing leaf | No — re-emit (passage tags pick it up if namespace already points at that leaf) |
| Add a text/`fields:` entry under context (or similar) | No — re-emit; coding form + `empty_coding` pick it up via `coding_schema` |
| Run emit + process | Yes — pipeline step, not shape-coupled code |

## Still intentional hand edits

| When | What |
|------|------|
| New **hashtag** surface (new passage namespace) | `namespaces` / `comment_tags` in the codebook YAML |
| New field should appear as a **projects-page overall chip** | `build_overall` / `projects.py` adapter (not schema-driven yet) |
| New **field kind** the schema builder does not understand | `coding_schema.py` (+ maybe emit) |
| Free-text extras not yet in YAML `fields:` | `_TEXT_EXTRAS` in `coding_schema.py` (move into codebook when you can) |
| Seed / real project codes | That project's `project.yaml` |
| Tests that pin concrete ids or version | Those tests |

## Retired as hand-edit touchpoints (12f)

- Hand-built Explicit/Implicit fieldsets in `site/coding.html` — now loops `coding_schema`
- Hardcoded governance / disclosure_format / policy_location lists in `coding_form.js`
- Parallel `empty_coding()` key lists in Python/JS — both derived from schema
- Layer-specific form helpers that only existed to feed the hand-built form

## Pipeline reminder

Re-emit is a **command** (`python -m open_research_tagging.emit_codebook`, then process comments/projects), not a place that must be taught each new value id. `codebook.json` includes `coding_schema` for the browser.
