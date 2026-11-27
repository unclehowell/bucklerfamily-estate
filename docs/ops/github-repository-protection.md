# GitHub repository protection and merge controls

**Repository:** `unclehowell/bucklerfamily-estate`  
**Default branch:** `main`  
**Production output branch:** `site`  
**Last repository-settings check:** 25 November 2026

## 1. Current observed settings

The connected GitHub repository metadata last reported:

| Setting | Observed state |
|---|---|
| Default branch | `main` |
| Branch protection on `main` | Not enabled (`protected: false`) |
| Automatically delete merged head branches | Disabled (`delete_branch_on_merge: false`) |
| Production Pages branch | `site` |

The connected GitHub installation permits repository/file/workflow reads and ordinary branch/PR operations, but does not provide the repository Administration write permission needed to change the protection or auto-delete settings. An owner with repository Administration access must apply the settings below.

## 2. Protect `main`

In GitHub:

1. Open the repository → **Settings** → **Branches** (or **Rules** → **Rulesets**, depending on the GitHub settings interface).
2. Add a branch protection rule / ruleset targeting exactly `main`.
3. Enable **Require a pull request before merging**.
4. Do not permit ordinary direct pushes to `main`. Keep any bypass list empty or tightly limited to a documented emergency owner/bot process.
5. Enable **Require status checks to pass before merging**.
6. Select the stable required check contexts listed below.
7. Save and verify the rule is active for `main`.

Recommended additional controls: require conversation resolution; dismiss stale approvals after new commits if approvals are used; require approval for changes from administrators where practicable. Choose the number of approvals to suit the project's actual human-review capacity rather than creating an unworkable gate.

### Required checks

The PR guard workflow now runs for every PR targeting `main`. It always emits the classifier and workflow-contract checks. The generated-site check is also represented on every PR; it runs the full generator for site/build-input changes and is skipped (a successful skip) for documentation/workflow-only changes.

Select these exact check contexts from GitHub's status-check picker:

| Check context | Purpose |
|---|---|
| `lint` | Changed-file editorial / agent lint |
| `scope-main` | Requires the `site-wide` label for changes to main |
| `Detect whether site content requires a full build` | Classifies PR paths; emitted for every PR |
| `Validate workflow syntax and privilege separation` | Parses the YAML and verifies read-only generator / privileged publisher separation |
| `Full generated-site build (no publish)` | Runs the full generator for changes to `tools/**`, `web/**`, `data/**`, themes, split-repo configuration and section pins; skipped for non-content changes |

Do **not** require `pin-section`: it is intentionally skipped for ordinary PRs into `main`. The `validate` check from `evidence-hierarchy-ci` is currently path-filtered to relevant data/tool/UI changes, so it is a supplemental targeted check rather than a universal required context. It must not be required globally until that workflow is changed to emit a stable check on every PR.

After saving, open a documentation-only PR and a representative content/data PR to confirm:
- both receive `lint`, `scope-main`, classifier and workflow-contract checks;
- documentation-only PRs skip the full generator without blocking;
- content/data PRs run the full read-only generator and cannot merge if it fails;
- no PR check has permission to publish to `site` or write build reports to `main`.

## 3. Enable GitHub's native merged-branch deletion

In GitHub:

1. Open repository → **Settings** → **General** → **Pull Requests**.
2. Enable **Automatically delete head branches**.
3. Save and confirm that a merged PR's topic branch is removed.

The repository already has a safe interim workflow, `.github/workflows/cleanup-merged-topic-branches.yml`, which runs after merges and main pushes. It only deletes same-repository branches whose merged PR is confirmed, whose current SHA still matches the merged PR head, and which are not used by an open PR. It preserves `main`, `site`, `agents`, `library`, and `archive/`, `release/`, and `migration/` branches. Native deletion is still preferable because it is a GitHub repository setting applied at merge time.

## 4. Keep production output protected

- Keep `main` as the source branch.
- Keep `site` as the generated Cloudflare Pages production branch.
- Do not make `site` the default branch.
- Do not allow direct human edits to generated `site` output. Make content changes in source branches/PRs, then let `build-cedwyn` generate and publish.
- The build pipeline serializes production runs and publishes only after the shared read-only site generator succeeds.
- Do not give the PR generator Cloudflare secrets or `contents: write` permission. Only the post-merge publisher has write access.

## 5. Verification record

When an owner applies the settings, record:
- the protection rule/ruleset name and target branch;
- exact required status contexts selected;
- whether administrator/bot bypasses exist and why;
- whether native delete-merged-head-branches is enabled;
- the test PRs used to confirm docs-only and content/data behavior;
- date and responsible owner.

Do not close the repository-hardening issue until the active settings are checked in GitHub and verified by a new PR.
