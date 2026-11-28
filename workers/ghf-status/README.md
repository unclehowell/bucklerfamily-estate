# ghf-status Worker — successor source and production deployment

**Status: deployed from this repository's `main` source on 28 November 2026.**

The live Cloudflare Worker `ghf-status` was updated from `workers/ghf-status/worker.js` at source commit `95eeb62c972378ab15209b9548517e04624d23dc`. New Cloudflare deployment ID: `294ffa00-d2c5-4de2-81fd-f3b1d13e5ab0`; version ID: `ff2f0a8d-c71b-40f5-b371-717f4ab49722`; 100% traffic.

## Source corrections
- Daily refresh registry reads from `unclehowell/bucklerfamily-estate/main/.github/daily-refresh/apps.json`.
- Central catalogue change detection reads `data/core` from `unclehowell/bucklerfamily-estate`.
- App change detection reads each dedicated app repository's `main` branch. The old central-repository mirror fallback has been removed.

## Preserved live settings
- D1 binding `DB`: `f26a7c7d-a3d8-4ee9-9311-5a97b29c8676`.
- KV binding `GHF_STATUS`: `350d63f198c94e1e841dfb5ec51bb361`.
- Secret binding `DIGEST_DRAIN_KEY`: preserved using Cloudflare's keep-existing-secret binding mechanism; its value was not read or changed.
- Cron schedules unchanged: `*/30 * * * *` and `35 4 * * *`.
- Existing public endpoint remains `/daily-refresh.json`, consumed by the GitHub-side `webapps-daily-odd` workflow.

## Verification
Cloudflare accepted the new Worker bundle. Settings read-back confirmed the same D1, KV and secret binding names; the cron read-back confirmed both schedules unchanged. A Browser Rendering read of `https://ghf-status.righteous.workers.dev/daily-refresh.json` returned the expected `cedwyn-daily-refresh-even/1.0` schema, 34 checked apps and no errors. The latest recorded even-side daily check at the time of the read was 04:35 UTC, as scheduled.

Source-contract test: `workers/ghf-status/source-contract.test.mjs`.
The source contains no live reference to the retired central repository.

Source: Cloudflare Worker settings, schedule and deployment read-backs; live endpoint response; GitHub source commit above.
