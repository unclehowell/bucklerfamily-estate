# Cloudflare routing and canonical host ownership

**Last verified:** 25 November 2026  
**Zone:** `bucklerfamily.estate`  
**Pages project:** `cedwyn`  
**Bridge Worker:** `cedwyn-agent-bridge`  
**General apex router:** `bfe-apex-router`

## 1. Production host model

The Cloudflare Pages project `cedwyn` serves the generated repository `site` branch. Its active custom domains include:

- `bucklerfamily.estate` — canonical public host;
- `cedwyn.bucklerfamily.estate` — project alias; Pages canonicalises GET requests to the apex;
- `cedwyn-datro.bucklerfamily.estate` — legacy project alias.

Treat `bucklerfamily.estate` as the canonical hostname for public site routes and the flow-watch event/health endpoints.

## 2. Opaque bridge route ownership

The fixed bridge path is consumed by the `cedwyn-agent-bridge` Worker. The route owner must be explicit on both the canonical apex and the `cedwyn` alias.

| Host / route pattern | Worker | Purpose |
|---|---|---|
| `bucklerfamily.estate/x78s8jej33i8f8rrj4is88*` | `cedwyn-agent-bridge` | Apex bridge endpoints |
| `bucklerfamily.estate/x78s8jej33i8f8rrj4is88/*` | `cedwyn-agent-bridge` | Apex bridge endpoints with slash path |
| `cedwyn.bucklerfamily.estate/x78s8jej33i8f8rrj4is88*` | `cedwyn-agent-bridge` | Alias compatibility |
| `cedwyn.bucklerfamily.estate/x78s8jej33i8f8rrj4is88/*` | `cedwyn-agent-bridge` | Alias compatibility |

The two apex route IDs were corrected on 25 November 2026:

- `3af623a74a104f89b2db7bf9e7dbd603`
- `0d6e0cf228814c94a3830c65388acb8b`

Their patterns were preserved; only the Worker binding changed from `bfe-apex-router` to `cedwyn-agent-bridge`.

The general `bfe-apex-router` remains responsible for the rest of the apex site. Do not assign the opaque bridge path to the general proxy: that proxy sent the canonical apex request back to the `cedwyn` alias.

## 3. Failure mode and repair

The incident sequence was:

1. A GET to `cedwyn.bucklerfamily.estate` was redirected by Cloudflare Pages to canonical `bucklerfamily.estate`.
2. The apex opaque-path route was owned by `bfe-apex-router`.
3. The general router proxied that request back to the alias.
4. The public health endpoint therefore returned a redirect rather than JSON.

The repair reassigned both apex opaque-path patterns directly to `cedwyn-agent-bridge`, retained alias routes for compatibility, and changed the workflow URLs to the canonical apex.

This is an infrastructure/routing issue; it is independent of the generated `site` branch and Pages file output.

## 4. Flow-watch URL ownership

The GitHub workflow `.github/workflows/flow-watch-events.yml` uses the canonical apex for:

- authenticated `POST /x78s8jej33i8f8rrj4is88/flow-event`;
- public `GET /x78s8jej33i8f8rrj4is88/flow-health.json`.

Do not change the worker hostname or route bindings without updating the workflow and the smoke-test URL together.

## 5. Verification

After any Pages domain, DNS or Worker-route change:

1. Query Cloudflare's zone Worker routes and confirm both apex patterns and alias patterns point to `cedwyn-agent-bridge`.
2. Confirm Pages project `cedwyn` has the canonical apex and `cedwyn` alias active.
3. Probe the public health URL on the canonical apex and require HTTP 200, `application/json`, non-empty body, schema `cedwyn.flow-watch/1.0`, a timestamp, a recognised status and typed issue-count/list fields.
4. Trigger or inspect the OIDC-authenticated flow-watch event signal and require `accepted: true`, `check.ok: true` and a valid health result.
5. Do not log the health payload's issue records or other D1 details; the workflow should report only the overall state and count.

Source: GitHub Actions, *Cedwyn flow-watch event signal*, run #45563031943 (25 November 2026): https://github.com/unclehowell/bucklerfamily.estate/actions/runs/45563031943. It reported an accepted event, `HEALTHY / 0 issues`, and a public GET returning HTTP 200 JSON (5,393 bytes).

## 6. Operational boundaries

- `main` contains application/workflow source; `site` is generated Pages output.
- Cloudflare Worker route bindings are account configuration and must be kept in sync with this record and the workflow.
- Do not change the opaque route patterns, remove the alias compatibility routes, or point the apex paths back to `bfe-apex-router` without a reviewed replacement and passing health test.
- Do not put API tokens, D1 credentials, private task records or email content in this document.
