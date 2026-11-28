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

## Access requirements

The relay authenticates to the Worker with a GitHub Actions OIDC token scoped to audience `bucklerfamily-estate-cms-relay`, repository `unclehowell/bucklerfamily-estate`, ref `refs/heads/main`, and the exact successor CMS relay workflow. The Worker verifies the token against GitHub's published JWKS. This removes the need for a duplicate `CMS_RELAY_KEY` Actions secret. App-repository writes still require the optional encrypted GitHub token stored by the editor to grant Contents write access to the selected app repo. The platform Actions token is used only for the central site build. If a selected app repo denies access, the relay retains the queue item and draft for retry rather than writing to the wrong repository.

## Data and rollback

No database or KV migration is performed. Keep the existing D1 database, CMS KV namespace, LIST service binding, password/session/agent/relay/drain secrets and routes. A Worker version rollback restores the previous deployed code while the durable KV/D1 data remains intact.
