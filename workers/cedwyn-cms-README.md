# cedwyn-cms Worker — legacy source snapshot

**Status: snapshot only — not safe to redeploy.**

The files in this directory were exported from the live Cloudflare Worker `cedwyn-cms` on 28 November 2026:
- `cedwyn-cms-legacy-index.js` — deployed Worker entry point
- `cedwyn-cms-legacy-engine.js` — deployed content engine

The deployment export also contained a separate `admin.txt` configuration part. It has deliberately **not** been copied into this repository because it is operational access configuration and must be handled as private Worker configuration, not source code.

The legacy engine explicitly sets `REPO = 'unclehowell/cedwyn'` and reads/writes the old CMS branches. A successor must replace that single-repository model with a verified per-app source resolver based on the canonical split manifest. Do not mechanically change the REPO constant to `bucklerfamily-estate`.

The live CMS Worker has a KV namespace, the D1 database `ghf-enquiries`, and a `LIST` service binding. Preserve its existing routes, KV, D1, service binding and private configuration until a replacement passes read/write tests and rollback checks.

Before any successor deployment:
1. Reconcile the live Worker export, old `cms` branch source and relay workflow.
2. Implement per-app source resolution and safe write/commit behaviour, including repositories whose app mode is `split-repo` and `deploy: repo`.
3. Migrate private admin configuration through a secret-safe mechanism; never commit it.
4. Test every CMS compartment, preview, authentication/authorization, stale-write rejection, branch protection, rollback and error path.
5. Confirm all existing D1/KV data is preserved and read-back verified.
6. Only then consider a separately approved production cutover.

No Worker, route, binding, secret, D1/KV data or public endpoint was changed by this snapshot.
