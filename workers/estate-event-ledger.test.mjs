import test from "node:test";
import assert from "node:assert/strict";
import { normalizeEvent } from "./estate-event-ledger.mjs";

const base = {
  event_type: "email.received",
  source_system: "gmail",
  source_id: "gmail-message-123",
  occurred_at: "2026-11-28T05:00:00Z",
  actor: "gmail-ingress",
  content_sha256: "a".repeat(64)
};

test("metadata events default to private and receive stable source idempotency", () => {
  const event = normalizeEvent(base, "2026-11-28T05:01:00Z", () => "event-1");
  assert.equal(event.privacy_class, "private");
  assert.equal(event.event_id, "event-1");
  assert.equal(event.idempotency_key, "gmail:gmail-message-123");
  assert.equal(event.processing_state, "received");
});

test("public metadata must be explicitly classified", () => {
  const event = normalizeEvent({ ...base, privacy_class: "public" }, "2026-11-28T05:01:00Z", () => "event-2");
  assert.equal(event.privacy_class, "public");
});

test("raw correspondence bodies and attachment payloads are rejected", () => {
  assert.throws(() => normalizeEvent({ ...base, body: "private email body" }), /payload_content_not_accepted/);
  assert.throws(() => normalizeEvent({ ...base, attachments: ["raw bytes"] }), /payload_content_not_accepted/);
  assert.throws(() => normalizeEvent({ ...base, nested: { contact: "person@example.com" } }), /payload_content_not_accepted/);
});

test("unknown fields and unknown related-id keys fail closed", () => {
  assert.throws(() => normalizeEvent({ ...base, arbitrary: "value" }), /unknown_event_field/);
  assert.throws(() => normalizeEvent({ ...base, related_ids: { email: "person@example.com" } }), /invalid_related_ids_key/);
});

test("invalid source, event type, timestamps and non-HTTPS URLs are rejected", () => {
  assert.throws(() => normalizeEvent({ ...base, source_system: "x" }), /invalid_source_system/);
  assert.throws(() => normalizeEvent({ ...base, event_type: "Email Received" }), /invalid_event_type/);
  assert.throws(() => normalizeEvent({ ...base, occurred_at: "not a date" }), /invalid_occurred_at/);
  assert.throws(() => normalizeEvent({ ...base, source_url: "http://example.com" }), /invalid_source_url/);
});

test("related IDs are allow-listed, bounded and deduplicated", () => {
  const event = normalizeEvent({ ...base, related_ids: { record_ids: ["EV-1", "EV-1", "EV-2"], task_id: "task-1" } });
  assert.deepEqual(JSON.parse(event.related_ids_json), { record_ids: ["EV-1", "EV-2"], task_id: "task-1" });
});

test("content hash and internal artifact references are validated", () => {
  assert.throws(() => normalizeEvent({ ...base, content_sha256: "not-hash" }), /invalid_content_sha256/);
  const noHash = { ...base }; delete noHash.content_sha256;
  assert.throws(() => normalizeEvent(noHash), /invalid_content_sha256/);
  assert.throws(() => normalizeEvent({ ...base, artifact_ref: "https://example.com/private.pdf" }), /invalid_artifact_ref/);
});
