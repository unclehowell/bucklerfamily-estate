# cedwyn-api Worker — multi-repository successor

**Source:** `workers/cedwyn-api/index.js`  
**Platform repository:** `unclehowell/bucklerfamily-estate`  
**Current live Worker:** `cedwyn-api` (unchanged until cutover)

The Worker no longer depends on `unclehowell/cedwyn`. Page-version history resolves each split app through the authoritative `split-repos.json` manifest and the matching theme configuration. App history uses the app's dedicated repository on `main`; shared data, journal and common web assets use `bucklerfamily-estate`. The Hive history route resolves to `cedwyn-hive/main/hive/`; the preserved `agents` and `library` branches resolve to the successor platform repository.

For split apps, history tries the original theme path and then the repository-root path. This covers apps whose split process stripped their former top-level directory. Old D1 version-cache records without an explicit repository identity are bypassed and refreshed, rather than serving stale links to the retiring repository.

The existing `cedwyn-apps` D1 database and tables remain bound to the Worker. The guestbook client bridge reads its asset from `bucklerfamily-estate/main`.

## Cutover safeguards

- Preserve existing D1 binding `DB` (UUID `6fb11d8e-5d14-41a4-a7a0-ebf3d3de410a`) and all secret bindings.
- Do not change routes, domains, CORS, caching or member access controls.
- Verify page-history results for split and central routes, including cache refresh.
- Verify `/api/catalogue`, `/api/v`, guestbook asset bridge and Academy endpoints.
- Keep the current deployed version available for rollback.
- This Worker is read-only with respect to GitHub; no repository write token is needed.

DATRO and all `*-datro` subdomains are outside scope and unchanged.
