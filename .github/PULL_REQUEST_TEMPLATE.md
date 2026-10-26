## Coding this change?

If this PR adds or updates files under `projects/`, leave **review comments on the Files tab** (not just conversation comments).

**Passage tags:** use the site **tag picker** (`tags.html`) → stage → Copy → paste hashtags at the top of the comment, then a short free-text note. Exact strings come from the picker — see [`codebook/COMMENTING.md`](../codebook/COMMENTING.md).

```text
#stance/permissive-with-conditions
#disclosure/required

Short free-text note about why this passage matters.
```

**Scope** needs type and position: `#scope/code:restricted`.

**Overall codes:** after refresh puts comments on the site, use the **coding view** (`coding.html?project=<slug>`) → Copy YAML → paste over the `coding:` block in `projects/<slug>/project.yaml`. Do not invent overall YAML by pasting random hashtags into `project.yaml`.

### Common mistakes

| Don’t | Do |
|-------|-----|
| `#Disclosure` | a picker tag such as `#disclosure/required` |
| `#stance permissive` | `#stance/…` with a value from the picker |
| `#scope/code` | `#scope/code:restricted` |

---

## Summary

-

## Checklist

- [ ] Provenance filled in `projects/<slug>/project.yaml` (source URL + commit hash) when adding a project
- [ ] Passage line comments use hashtags from the tag picker (`#namespace/value`)
- [ ] Overall `coding:` updated via coding view Copy YAML when coding the whole policy
