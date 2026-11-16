# Pending workflow changes (issue #4)

The agent's GitHub connector cannot write under `.github/workflows/` (it lacks the `workflow` scope),
so these two files are staged here for the owner to put in place. Nothing in this folder runs.

1. Move `split-repo-watch.yml` to `.github/workflows/split-repo-watch.yml`.
2. Apply `build.yml.patch` to `.github/workflows/build.yml` (`git apply tools/workflows-pending/build.yml.patch`).
   It only adds the `repository_dispatch: types: [split-repo-deploy]` trigger. Optional: the watcher works without it.

What the watcher does: for every `deploy: repo` app in `split-repos.json`, it compares the app repo's main HEAD with the
commit stamped for it in the live site's `_cedwyn/reports/_assemble_report.json`. If any app is ahead and no build-cedwyn
run is queued or running, it dispatches `build.yml`. It uses only this repository's `GITHUB_TOKEN` (`actions: write`), so
no new secret is needed. It runs every 15 minutes (when GitHub fires the schedule), after every build-cedwyn run, on
`repository_dispatch: split-repo-deploy`, and by hand. Guards: no re-dispatch after a failed build; after a successful
build, app commits older than that build's start are ignored; apps the report does not stamp are ignored.

Tested locally against the live report on 16 Nov 2026: 72 apps checked, 4 ahead (mr-wolf, fcg, forensic,
that-old-chestnut).
