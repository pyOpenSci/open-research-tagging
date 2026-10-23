# How to tag on a pull request

Use **PR review comments** on the Files tab (line or multi-line). Put codebook hashtags on their own lines at the top of the comment, then a short free-text note.

**Exact hashtag strings come from the tag picker** — not from a hand-maintained list in this file. The codebook source is [codebook.yaml](codebook.yaml) (draft); the picker shows every valid tag the site and tag-check accept.

## Workflow

1. Open the **tag picker** on the site (`tags.html`). Locally: `cd site && python3 -m http.server 8000`, then http://localhost:8000/tags.html (GitHub Pages URL later).
2. Search if needed; **click a tag** to stage it. Stage several if the passage needs more than one code.
3. **Copy** — multiline hashtags only, one per line.
4. On the PR **Files** tab, start a review comment on the relevant line(s), paste the hashtags at the top, then add one or two sentences under them.
5. After comments land, maintainers refresh site data (`fetch_comments` → `process_comments` / Actions). Malformed tags (e.g. `#Disclosure` with no `/value`) get a bot reply and can fail the PR check; unknown-but-well-formed ids are soft while the codebook is draft.

## Shape of a comment

```text
#stance/permissive-with-conditions
#disclosure/required

One or two sentences on what this passage shows.
```

(Those example hashtags are illustrative — prefer Copy from the picker so spelling matches the codebook.)

## Rules (short)

1. **Lowercase** hashtags.
2. Always **`#namespace/value`** — a slash is required.
3. **Scope** is special: `#scope/<type>:<position>` (colon between type and position). The picker lists every valid pair.
4. Unknown values can still show on the site while the codebook is draft; bare `#Disclosure` with no `/value` will **not** parse.

## Common mistakes

| Don’t write | Write instead |
|-------------|----------------|
| `#Disclosure` | a picker tag such as `#disclosure/required` |
| `#stance` or `#stance permissive` | `#stance/…` with a value from the picker |
| `#scope/code` | `#scope/code:restricted` (type **and** position) |
| Conversation comment on the PR | Review comment on the **Files** tab (needs a line) |

## Which tool when

| Need | Where |
|------|--------|
| Tag a **passage** (line evidence) | **Tag picker** (`tags.html`) → Copy hashtags → paste into a **Files-tab** review comment (this doc). |
| Browse tagged passages | Comment browser (`index.html`) after maintainers refresh site data. |
| Set **overall** codes for the policy | **Coding view** (`coding.html?project=<slug>`) → walk evidence → **Copy YAML** → paste over the `coding:` block in `projects/<slug>/project.yaml`. |

Do **not** invent overall YAML by pasting random hashtags into `project.yaml`. Passage hashtags stay on PR comments; overall codes stay in `project.yaml`.
