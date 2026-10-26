# Codebook update touchpoints (from 12e)

When `codebook/codebook.yaml` changes shape (not just labels), these layers often need a hand update. Goal: shrink this list over time so a content-only YAML edit is enough.

## Touched in 12e (Explicit / Implicit subsections)

| Layer | What had to change | Why it wasn't data-driven |
|-------|--------------------|---------------------------|
| `codebook/codebook.yaml` | Nested `explicit` / `implicit` under each dimension; new ids; namespace `path`s | Source of truth (expected) |
| `src/.../codebook.py` | Scope namespace must resolve `path` (was using dimension id only → broke on `scope.explicit`) | Indexer assumed flat scope |
| `src/.../codebook_emit.py` | Emit optional `scope_implicit` via public `index_scope_labels` / `resolve_dimension_path` | JSON schema is hand-shaped; second scope block not generic |
| `src/.../coding_yaml.py` | Entire nested emit + flat→explicit lift | Explicit adapter for `project.yaml` shape (by design, 5c/10c) |
| `site/js/coding_form.js` | Mirror of coding_yaml + form helpers | Same adapter, duplicated in JS (emit-drift) |
| `site/js/coding.js` | `scopeRows` / `scopePositions` take layer | Form API tied to HTML |
| `site/coding.html` | Explicit/Implicit subsections in markup | Form not generated from codebook tree |
| `src/.../projects.py` | `_coding_explicit_view` flatten for overall chips; context from `explicit` | Overall table still Explicit-only; adapter not generic |
| `projects/_template/project.yaml` | Nested coding skeleton | Template not generated from codebook |
| `projects/pyopensci/project.yaml` | Migrated seed coding | Seed content |
| `site/data/*.json` | Re-emit / reprocess | Pipeline output |
| Tests | Version smoke, emit golden, form defaults, walkthrough selectors, build_project assertions | Tests encode shape |

## Still hardcoded (future ease targets)

- **Governance / policy_location / disclosure_format options** in `coding_form.js` (not always in `codebook.json` `values`).
- **Coding form HTML** — one fieldset per dimension written by hand; adding a leaf means editing HTML + JS + Python emit.
- **Passage tag namespaces** — Implicit mostly overall-only; new passage tags need `namespaces` + `comment_tags` + catalog.
- **Projects-page filters** — Explicit overall only; Implicit not in `filter_order`.
- **Synthetic `minimal_codebook` fixture** — still flat (good for unit tests); real draft smoke is separate.

## What already survives a content-only edit

- New **value ids** under an existing leaf (with namespace path) → tags, chips, soft-unknowns work after re-emit.
- Label/description-only changes → re-emit; ids stable.

## Ideas to make updates easier

1. Generate coding-form sections (or a thin config) from the codebook dimension tree.
2. Emit full dimension tree (or form schema) in `codebook.json` so JS stops hardcoding enums.
3. Keep Python `emit_coding_block` as contract; generate JS emit from it, or share one implementation.
4. Public helpers for scope indexing instead of importing `_`-prefixed functions in emit.
