# ghf-status Worker — successor source candidate

**Status: migration candidate only. Not deployed.** This source was exported from the live Cloudflare Worker on 28 November 2026 and updated for the central repository retirement.

## Source corrections
- Daily refresh registry now comes from `unclehowell/bucklerfamily-estate/main/.github/daily-refresh/apps.json`.
- Central catalogue change detection reads `data/core` from `unclehowell/bucklerfamily-estate`.
- App change detection reads each dedicated app repository's `main` branch. The old `mirror` fallback into `unclehowell/cedwyn` has been removed.

## Live settings to preserve
- Current Worker name: `ghf-status`.
- Verified cron schedules: `*/30 * * * *` and `35 4 * * *`.
- The existing public endpoint `/daily-refresh.json` is consumed by the GitHub-side daily refresh workflow.
- Preserve current Worker routes, bindings, environment configuration, cache behaviour and response schema during cutover. This snapshot does not change settings or infer unexposed state.

## Required before deployment
1. Run the source-contract test and syntax check.
2. Compare the packaged candidate with the live export and record the exact intended diff.
3. Test `/daily-refresh.json` in an isolated preview with successor registry data.
4. Verify every refresh registry record matches the successor `split-repos.json` mode and `deploy` values.
5. Confirm the odd-side workflow receives the even-side response, skips direct-deploy app syncs, and triggers at most one build.
6. Test stale/empty/error cases and rollback.
7. Only then consider a separate production Worker cutover.

No cron, route, secret, binding, state or production endpoint is changed by this source snapshot.
