# Repository split — active production architecture

**Canonical central repository:** [`unclehowell/bucklerfamily-estate`](https://github.com/unclehowell/bucklerfamily-estate)  
**App inventory:** [`split-repos.json`](../split-repos.json) on `main`  
**Current migration tracking:** [Issue #4](https://github.com/unclehowell/bucklerfamily-estate/issues/4) (direct-source app deployment) · [Issue #19](https://github.com/unclehowell/bucklerfamily-estate/issues/19) (retire the old central repository as an active source)

## Source of truth

`unclehowell/bucklerfamily-estate` is the active central repository for the BucklerFamily.estate production build, catalogue data, site-wide tooling, shared runtime assets, workflows and public engineering issues.

The central build runs from this repository's `main` branch and publishes the assembled site to this repository's `site` branch. Cloudflare Pages serves that branch. The Cloudflare Pages project is still internally named `cedwyn` and retains the existing custom-domain bindings; that internal project name is not the GitHub source repository.

The workflow's historical display name is `build-cedwyn`. It runs **inside `unclehowell/bucklerfamily-estate`**. Its name does not mean it checks out or builds from the retired `unclehowell/cedwyn` repository.

The old central repository `unclehowell/cedwyn` is historical only. Do not use it for new central-site changes, production builds, issue tracking, or as a fallback source.

## Dedicated webapp repositories

Every durable webapp with a `deploy: "repo"` entry in `split-repos.json` is assembled directly from its dedicated repository (normally its `main` branch). The build records the exact repository, commit and output directory in its assembly report. If a declared repository or its `index.html` is missing, the build fails for that app; it does not fall back to an old branch from `unclehowell/cedwyn`.

Examples include:

| App | Dedicated source | Public path |
|---|---|---|
| Mr Wolf | `unclehowell/cedwyn-mr-wolf` | `/mr-wolf/` |
| Hive | `unclehowell/cedwyn-hive` | `/hive/` |
| Chessboard | `unclehowell/cedwyn-chess` | `/chess/` |
| Research Library | `unclehowell/cedwyn-research` | `/research/` |

The `cedwyn-` prefix on some dedicated app repository names is a historical naming convention for those individual apps. It does not make `unclehowell/cedwyn` the central repository.

Other source modes are governed by their explicit entries in `themes.json` and `split-repos.json`. Any retained snapshot branches are owned by and read from this repository's own refs; they are not fetched from the retired central repository.

## Where to send work

| Kind of change | Where to open the PR |
|---|---|
| One webapp's content, assets, worker or app-local tools | That webapp's dedicated repository named in `split-repos.json` |
| Site-wide rules, catalogue core, shared runtime, central build, Academy, lint or navigation | `unclehowell/bucklerfamily-estate` on `main` |
| Build-only, pin or source-inventory changes | `unclehowell/bucklerfamily-estate` on `main` |

GitHub Issues in `unclehowell/bucklerfamily-estate` are the canonical public engineering work ledger. HubSpot remains restricted to private correspondence and review tasks.

## How to work on one webapp

1. Read the app's row in [`split-repos.json`](../split-repos.json).
2. Confirm its declared source repository and `deploy` mode.
3. Clone that dedicated repository and make app-local changes there.
4. Open the PR against that repository's `main`.
5. After merge, the central build assembles the declared source into the matching path on the apex site.

For site-wide or multi-app changes, work in `unclehowell/bucklerfamily-estate` instead.

## Production path

`unclehowell/bucklerfamily-estate` `main` → `build.yml` / `build-cedwyn` → `site` → Cloudflare Pages project (internal name `cedwyn`) → `https://bucklerfamily.estate`.

No domain is detached by this repository split. The existing `cedwyn.bucklerfamily.estate` hostname remains a legacy alias; the canonical public site is `bucklerfamily.estate`.

## Historical records

The former central repository and its old branches remain available for provenance and historical commit links. Old `SPLIT.json` values, migration reports, commit references and the former issue #582 are historical records only. They must not be treated as current build-source configuration or current work-tracking destinations.

— BucklerFamily.estate repository instructions
