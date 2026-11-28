# Estate event ingress — implementation candidate

**Status: code and schema candidate only. Not deployed.**

This is the first bounded implementation step of the event-sourced research architecture. It does not provision a Worker, D1 database, Queue, Workflow, R2 bucket, route, DNS entry, secret or agent runner.

## Contract

- Authenticated `POST /v1/events` accepts a strict metadata envelope only.
- Maximum request body is 16 KiB.
- Original email/document bodies, attachment bytes, drafts, contact data and credentials are rejected rather than copied into the ledger.
- Unknown fields fail closed.
- Source identity is idempotent on `(source_system, source_id)`.
- Replayed events with the same content hash return the original event ID; the same source ID with a different hash returns HTTP 409 for quarantine/review.
- Privacy defaults to `private`; there is no public event-read endpoint.
- Successful ingest writes an `event_log` row and a pending `classify` job in one D1 workflow path.
- The event record contains provenance references, IDs and hashes, never the raw source payload.
- `GET /health` reveals only service/schema identity, not bindings, database IDs or state.

## Files

- `estate-event-ledger.mjs` — Worker ingress and pure envelope normalisation.
- `estate-event-ledger.sql` — D1 schema for append-only events and durable job outbox.
- `estate-event-ledger.test.mjs` — unit tests for strict validation and privacy boundaries.

## Activation requirements

Before any live deployment:
1. Provision a new, dedicated D1 database only after cost, retention, privacy and export/rollback review.
2. Configure a high-entropy `INGEST_TOKEN` as a Cloudflare secret; never place it in source, GitHub, logs or browser code.
3. Bind only the dedicated database as `EVENT_DB`; never reuse `cedwyn-apps`, `ghf-enquiries`, or any current production database.
4. Apply the SQL migration and verify constraints with duplicate, content-conflict and private-payload tests.
5. Authenticate source adapters individually. Gmail, GitHub, HubSpot and archive ingress are not live merely because the Worker exists.
6. Add a Queue/Workflow consumer only when a real agent runner, lease model, retry policy and spend limit are verified.
7. Keep event bodies in their original systems of record or approved private object storage; this D1 schema stores metadata only.

No recipient-facing email, FOI request, publication, route change or production data migration is part of this implementation.
