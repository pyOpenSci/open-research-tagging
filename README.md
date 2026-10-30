# Open research tagging

This project supports qualitative research on how open-source communities treat AI-generated contributions. Researchers copy project AI policies into this repository, then apply a shared **codebook** to that text: passage-level tags on specific lines, and overall codes for the policy as a whole.

Coding happens on GitHub, not in a custom app. Policy files live under `projects/<slug>/`. Coders open a pull request and leave **review comments on the Files tab**, using codebook hashtags (for example `#disclosure/required`). Maintainer tooling fetches those comments, turns them into JSON, and publishes a **static site** where anyone can browse, filter, and follow evidence links. The site never writes back to the repo—GitHub remains the editor of record.

Helpers on the site speed up the awkward parts: a **tag picker** stages the exact hashtag strings for paste into review comments, and a **coding view** walks passage evidence and emits a paste-ready `coding:` YAML block for `project.yaml`. Exact tag strings always come from the codebook (via the picker), not from memory.

**Live site:** [https://www.pyopensci.org/open-research-tagging/](https://www.pyopensci.org/open-research-tagging/)  
**How to add a project:** [below](#how-to-add-a-project)  
**How to tag on a PR:** [`codebook/COMMENTING.md`](codebook/COMMENTING.md)  
**How the pieces fit:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## How to add a project

### Setup

1. On a **new branch** (not `main`), create a new folder with the name of the project as the folder name.
2. Copy the `project.yaml` file in [`projects/_template/`](projects/_template/) into `projects/<slug>/`.
3. Edit `project.yaml`. The `slug` should be the same as the folder name. If you want a different display name, add a `display_name`. Optionally fill **provenance** (`source_repo`, `source_commit`, optional `source_url`, `retrieved_at`, `notes`), but you can always come back to that.
4. Move project files such as READMEs, Contributing Guides, AI policy docs, etc into the project folder and give them corresponding entries in `project.yaml` under the files list.
5. Open a **pull request**. This will trigger a GitHub action that re-deploys the site with your project listed. Check [the projects page](https://www.pyopensci.org/open-research-tagging/projects.html) to confirm.

Note: once you create the project folder with `project.yaml` (steps 1 and 2) you should be able to open a PR without any other steps and the site should still deploy fine. So you can technically skip steps X-Y and come back to them incrementally if you want to.

### Tagging & Coding

There are two types of tagging/coding you'll want to do.

**Comment tags.** These mark a specific passage (a line or range in a policy file) with codebook hashtags such as `#disclosure/required`. Use the [tag picker](https://www.pyopensci.org/open-research-tagging/tags.html) to stage and copy the exact strings, then paste them into a **Files-tab** comment on the PR (details: [`COMMENTING.md`](codebook/COMMENTING.md)). After you comment, someone needs to run **Actions → Update comment data** (or wait for the daily run) so the site picks them up. They show up in the [comment browser](https://www.pyopensci.org/open-research-tagging/) (filter by project) and as evidence in the coding view.

**Project-level coding.** These are the overall codes for the whole policy (stance, scope, accountability, and so on) stored under `coding:` in `project.yaml` — not as hashtags on lines. Open the [coding view](https://www.pyopensci.org/open-research-tagging/coding.html) for your project slug, walk the comment evidence, fill the form, then **Copy YAML** and paste over `projects/<slug>/project.yaml` on the PR.

## Layout


| Path                         | Role                                                                |
| ---------------------------- | ------------------------------------------------------------------- |
| `projects/<slug>/`           | Policy files + `project.yaml` (provenance + overall `coding:`)      |
| `projects/_template/`        | Starter for a new project slug                                      |
| `codebook/`                  | `codebook.yaml` + COMMENTING guide                                  |
| `site/`                      | Static Pages site (`index`, `projects`, `tags`, `coding` + `data/`) |
| `src/open_research_tagging/` | Pipeline package (fetch, process, tag-check, emit)                  |
| `.github/workflows/`         | Tests, tag-check, comment refresh, Pages deploy                     |


GitHub is the editor. The site is read-only.

## Two coding layers


| Layer       | Where                                 | Helper                                                                                       |
| ----------- | ------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Passage** | Hashtags on Files-tab review comments | [Tag picker](https://www.pyopensci.org/open-research-tagging/tags.html)                      |
| **Overall** | `coding:` in `project.yaml`           | [Coding view](https://www.pyopensci.org/open-research-tagging/coding.html?project=pyopensci) |


**Typical coder path:** tag picker → paste on the Files tab → maintainers refresh site data → coding view → Copy YAML over `project.yaml`. PR checklist: [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

## Setup (dev)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium   # once; needed for site integration tests
pytest
```



## Local site preview

```bash
cd site && python3 -m http.server 8000
```


| URL                                                                                                        | Page                     |
| ---------------------------------------------------------------------------------------------------------- | ------------------------ |
| [http://localhost:8000/](http://localhost:8000/)                                                           | Comment browser          |
| [http://localhost:8000/projects.html](http://localhost:8000/projects.html)                                 | Projects / overall codes |
| [http://localhost:8000/tags.html](http://localhost:8000/tags.html)                                         | Tag picker               |
| [http://localhost:8000/coding.html?project=pyopensci](http://localhost:8000/coding.html?project=pyopensci) | Coding view              |


Committed `site/data/*.json` is an **offline fixture snapshot** for local preview. Public Pages gets **live** JSON built in Actions (not committed to `main`). Playwright uses a temp copy of `site/` filled from `raw_comments.fixture.json`. Details: ARCHITECTURE → *Fixture vs live site JSON*.

## Workflows


| Workflow                | When                                                            | What                                                                                |
| ----------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Tests** (`test.yml`)  | Push to `main`, PRs                                             | `pytest` (incl. Playwright)                                                         |
| **Check comment tags**  | Files-tab comment create/edit; PR open/sync                     | Soft bot reply on bad tags; PR scan hard-fails **malformed** only                   |
| **Update comment data** | Daily cron + manual                                             | Fetch → process (incl. open-PR projects) → deploy Pages (**no** git commit of JSON) |
| **Deploy Pages**        | `site/` / `projects/` / `codebook/` (etc.) on `main`, or manual | Rebuild live JSON in CI → publish `site/` (**no** git commit)                       |




### Draft-codebook tag-check policy

While the codebook is still changing, tag-check **hard-fails the PR check only on malformed tags** (e.g. bare `#Design`, unparseable `#…`). Well-formed but unknown ids (e.g. `#stance/not-in-codebook-yet`) are still reported (and can get a reply / `needs_tag_review` on the site) but do **not** fail the status check. Reply jobs use `--soft` (always green). Prefer **Add single comment** or **Submit** the review so replies can attach — see COMMENTING.md.

## GitHub Pages

Production host is the **pyOpenSci** org repo. One-time setup (already done for production):

1. **Settings → Pages → Build and deployment → Source:** GitHub Actions.
2. Push workflows on `main` (or merge a PR that adds `.github/workflows/`).
3. Run **Actions → Update comment data → Run workflow** once (or wait for the daily cron) so Pages gets live comments (JSON is built in CI, not committed).
4. Smoke-check: comments browser, projects, **tag picker**, **coding view**.

**Org production URL:** [https://www.pyopensci.org/open-research-tagging/](https://www.pyopensci.org/open-research-tagging/)  
**Personal/test staging (optional):** [https://shaunagm.github.io/open-research-tagging/](https://shaunagm.github.io/open-research-tagging/)