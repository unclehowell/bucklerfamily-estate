# Estate CMS Worker — multi-repository source

**Worker:** `cedwyn-cms`  
**Route:** existing `cedwyn.bucklerfamily.estate/admin/*` route  
**Source:** this directory in `unclehowell/bucklerfamily-estate`.

The estate CMS no longer reads or writes `unclehowell/cedwyn`.

- `workers/cedwyn-cms/engine.js` resolves each split app to its dedicated repository and `main` branch using central `themes.json` + `split-repos.json`.
- `bucklerfamily-estate` remains the platform/catalogue source for shared site files and root JSON data.
- Each dedicated app repository is the only write target for its CMS compartment.
- `relay/relay.mjs` uses the same repository-aware guarded commit engine.
- The scheduled relay workflow checks out the successor's `main` branch, not a legacy `cms` branch.
- Existing CMS KV drafts, queue, audit log and encrypted optional GitHub token remain in the current KV namespace; existing D1, service bindings and Worker secrets are preserved during deployment.
- Pre-migration queue items without a repository identity are failed closed as stale and kept in the audit log; they are not committed to the new platform or a guessed app repository. The saved drafts remain available for re-basing.

## Queue execution

The CMS Worker owns its queue drain. Cloudflare Cron Trigger `*/5 * * * *` invokes the Worker's `scheduled` handler, which reads the encrypted optional GitHub token from the existing CMS KV namespace and performs the same per-repository guarded commit. No GitHub Actions relay secret or cross-repository Actions token is required. If no token is stored, or the token cannot read/write the selected app repository, the queued item and draft remain in KV for retry. The prior GitHub Actions relay workflow is no longer used.

## Access requirements

The optional `CMS_CROSS_REPO_TOKEN` Actions secret, or the encrypted optional token stored by the editor, must grant Contents write access to each repository being edited. The fallback GitHub Actions token has access only to this platform repository; it is not falsely treated as cross-repository authority. If no cross-repository write permission exists, the job fails safely and retains the draft rather than writing to the wrong repository.

## Data and rollback

No database or KV migration is performed. Keep the existing D1 database, CMS KV namespace, LIST service binding, password/session/agent/relay/drain secrets and routes. A Worker version rollback restores the previous deployed code while the durable KV/D1 data remains intact.
