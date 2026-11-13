# Apex router

Source snapshot for the deployed Cloudflare Worker `bfe-apex-router`.

This is a platform routing Worker, not a webapp. It presents the estate's site at `https://bucklerfamily.estate/<app>/`, reads `/areas.json` from the configured `ORIGIN`, and proxies or rewrites requests. Its Cloudflare route table is managed in the account and is deliberately not recreated by this source file.

## Current bindings

| Binding | Type | Current value |
|---|---|---|
| `ORIGIN` | Plain text | `https://cedwyn.bucklerfamily.estate` |
| `APEX_PAGES` | Plain text | `https://bucklerfamilyfarm.pages.dev` |

`APEX_PAGES` remains the separate BucklerFamilyFarm Pages origin for paths in `KEEP`. `ORIGIN` currently remains the old Cedwyn origin and must not be changed until the successor Pages project has a successful deployment and all staging routes have passed smoke checks.

## Handover order

1. Build and publish `unclehowell/bucklerfamily-estate` to its own Pages project.
2. Verify the staging hostname, root, `/areas.json`, `/academy/`, `/library/`, `/theories/`, `/spill/`, catalogue and `/db/` chunks.
3. Only then set `ORIGIN` to the verified successor Pages hostname.
4. Keep the existing Worker routes and `APEX_PAGES` binding unchanged.
5. After the binding change, check apex paths, redirects, app registry and the opaque agent-bridge route. Roll back `ORIGIN` to the old hostname if any smoke check fails.

## Guardrails

- Do not change DNS, Pages domains or Worker routes from this file.
- Do not use the apex Pages project as a catch-all fallback; it is a separate site and can return soft-200s.
- Preserve the distinct old subdomain constant used by the request/response rewrite logic unless a separately reviewed code change demonstrates it is no longer needed.
- Deploys must preserve compatibility date `2025-01-01`, flag `global_fetch_strictly_public`, bundled usage model, and observability settings. The Worker has no secret bindings.
- A change to `ORIGIN` is a cutover action and must follow staging verification; a code deploy alone is not a cutover.
