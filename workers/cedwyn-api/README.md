# cedwyn-api Worker — migration snapshot

This directory preserves the source exported from the deployed Cloudflare Worker `cedwyn-api` on 28 November 2026.

**Status: SNAPSHOT ONLY — NOT SAFE TO REDEPLOY.**

The deployed Worker still contains:
- `const REPO = "unclehowell/cedwyn"`;
- page/version history lookups that resolve legacy theme branch and folder pairs in that repository;
- a direct guestbook asset fetch from `unclehowell/cedwyn/main/web/_cedwyn/guestbook/gb.js`.

Those are active retirement blockers. Do not change the `REPO` constant to `unclehowell/bucklerfamily-estate` as a mechanical substitution: the central site now sources each app from its dedicated repository, so the API needs a per-app source map derived from the canonical split manifest and verified against the live theme configuration.

The Worker also binds to the existing D1 database `cedwyn-apps`. Preserve that database and its tables. No schema migration, data export, route change, secret change or deployment is included by this snapshot.

Before a successor deploy:
1. Replace legacy branch lookups with a verified app-repository source resolver.
2. Move the guestbook client asset to a stable app/platform asset path and update its reference.
3. Add route and source-resolution tests, including direct-repo, legacy read-only, unknown theme and missing-file cases.
4. Verify every API route against the existing D1 schema without changing data.
5. Prove the Worker binding, route, cache behavior, CORS/auth controls and rollback.
6. Export and verify the D1 database before any future schema/data migration.

The file is an exact source snapshot, not a production-ready successor.
