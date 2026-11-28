const MAX_BODY_BYTES = 16 * 1024;
const SOURCES = new Set(["gmail", "github", "cloudflare", "hubspot", "catalogue", "archive", "manual"]);
const RELATED_KEYS = new Set(["task_id", "request_id", "record_ids", "entity_ids", "institution_ids", "project_ids"]);
const FORBIDDEN_KEYS = new Set(["body", "content", "raw", "attachments", "draft", "email", "recipient", "contact", "address", "password", "token", "secret"]);

const json = (value, status = 200) => new Response(JSON.stringify(value), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff" }
});

const fail = (code, status) => json({ ok: false, error: code }, status);

function hasForbiddenKey(value) {
  if (!value || typeof value !== "object") return false;
  for (const [key, child] of Object.entries(value)) {
    if (FORBIDDEN_KEYS.has(key.toLowerCase())) return true;
    if (hasForbiddenKey(child)) return true;
  }
  return false;
}

function isoTimestamp(value, field) {
  if (typeof value !== "string" || value.length > 40) throw new Error("invalid_" + field);
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) throw new Error("invalid_" + field);
  return date.toISOString();
}

function relatedIds(value) {
  if (value === undefined || value === null) return {};
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid_related_ids");
  const out = {};
  for (const [key, raw] of Object.entries(value)) {
    if (!RELATED_KEYS.has(key)) throw new Error("invalid_related_ids_key");
    if (Array.isArray(raw)) {
      if (raw.length > 100 || raw.some(x => typeof x !== "string" || !x.trim() || x.length > 128)) {
        throw new Error("invalid_related_ids");
      }
      out[key] = [...new Set(raw.map(x => x.trim()))];
    } else {
      if (typeof raw !== "string" || !raw.trim() || raw.length > 128) throw new Error("invalid_related_ids");
      out[key] = raw.trim();
    }
  }
  return out;
}

/**
 * Validate the strict event envelope. The original message/document payload is never accepted.
 * source_id is the idempotency anchor from the upstream system; event_id is local to this ledger.
 */
export function normalizeEvent(input, now = new Date().toISOString(), idFactory = () => crypto.randomUUID()) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("invalid_event");
  if (hasForbiddenKey(input)) throw new Error("payload_content_not_accepted");

  const allowed = new Set([
    "event_type", "source_system", "source_id", "source_url", "occurred_at", "actor",
    "related_ids", "content_sha256", "privacy_class", "supersedes_event_id", "artifact_ref"
  ]);
  if (Object.keys(input).some(key => !allowed.has(key))) throw new Error("unknown_event_field");

  const eventType = typeof input.event_type === "string" ? input.event_type.trim() : "";
  if (!/^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$/.test(eventType) || eventType.length > 100) {
    throw new Error("invalid_event_type");
  }

  const sourceSystem = typeof input.source_system === "string" ? input.source_system.trim().toLowerCase() : "";
  if (!SOURCES.has(sourceSystem)) throw new Error("invalid_source_system");

  const sourceId = typeof input.source_id === "string" ? input.source_id.trim() : "";
  if (!sourceId || sourceId.length > 240) throw new Error("invalid_source_id");

  const actor = typeof input.actor === "string" ? input.actor.trim() : "";
  if (!actor || actor.length > 100 || /[@\s]/.test(actor)) throw new Error("invalid_actor");

  const privacy = input.privacy_class === undefined ? "private" : input.privacy_class;
  if (privacy !== "private" && privacy !== "public") throw new Error("invalid_privacy_class");

  let sourceUrl = null;
  if (input.source_url !== undefined && input.source_url !== null && input.source_url !== "") {
    if (typeof input.source_url !== "string" || input.source_url.length > 2000) throw new Error("invalid_source_url");
    let parsed;
    try { parsed = new URL(input.source_url); } catch { throw new Error("invalid_source_url"); }
    if (parsed.protocol !== "https:") throw new Error("invalid_source_url");
    sourceUrl = parsed.toString();
  }

  const contentHash = input.content_sha256 ?? null;
  if (contentHash !== null && (typeof contentHash !== "string" || !/^[a-f0-9]{64}$/i.test(contentHash))) {
    throw new Error("invalid_content_sha256");
  }

  const supersedes = input.supersedes_event_id ?? null;
  if (supersedes !== null && (typeof supersedes !== "string" || !supersedes.trim() || supersedes.length > 200)) {
    throw new Error("invalid_supersedes_event_id");
  }

  const artifactRef = input.artifact_ref ?? null;
  if (artifactRef !== null && (typeof artifactRef !== "string" || !artifactRef.trim() || artifactRef.length > 512 || /^https?:/i.test(artifactRef))) {
    throw new Error("invalid_artifact_ref");
  }

  const occurredAt = isoTimestamp(input.occurred_at, "occurred_at");
  const ingestedAt = isoTimestamp(now, "ingested_at");
  const related = relatedIds(input.related_ids);

  return {
    event_id: idFactory(),
    event_type: eventType,
    source_system: sourceSystem,
    source_id: sourceId,
    source_url: sourceUrl,
    occurred_at: occurredAt,
    ingested_at: ingestedAt,
    actor,
    related_ids_json: JSON.stringify(related),
    content_sha256: contentHash ? contentHash.toLowerCase() : null,
    privacy_class: privacy,
    idempotency_key: sourceSystem + ":" + sourceId,
    processing_state: "received",
    supersedes_event_id: supersedes,
    artifact_ref: artifactRef
  };
}

async function tokenMatches(provided, expected) {
  if (!provided || !expected) return false;
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(provided)),
    crypto.subtle.digest("SHA-256", enc.encode(expected))
  ]);
  const left = new Uint8Array(a), right = new Uint8Array(b);
  let difference = 0;
  for (let i = 0; i < left.length; i++) difference |= left[i] ^ right[i];
  return difference === 0;
}

async function persistEvent(db, event) {
  const insert = await db.prepare(`
    INSERT INTO event_log (
      event_id, event_type, source_system, source_id, source_url, occurred_at, ingested_at,
      actor, related_ids_json, content_sha256, privacy_class, idempotency_key,
      processing_state, supersedes_event_id, artifact_ref
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source_system, source_id) DO NOTHING
  `).bind(
    event.event_id, event.event_type, event.source_system, event.source_id, event.source_url,
    event.occurred_at, event.ingested_at, event.actor, event.related_ids_json,
    event.content_sha256, event.privacy_class, event.idempotency_key,
    event.processing_state, event.supersedes_event_id, event.artifact_ref
  ).run();

  if ((insert.meta?.changes ?? 0) > 0) {
    await db.prepare(`
      INSERT INTO event_jobs (job_id, event_id, work_type, state, attempt_count, created_at, updated_at)
      VALUES (?, ?, 'classify', 'pending', 0, ?, ?)
      ON CONFLICT(event_id, work_type) DO NOTHING
    `).bind(crypto.randomUUID(), event.event_id, event.ingested_at, event.ingested_at).run();
    return { duplicate: false, event_id: event.event_id };
  }

  const existing = await db.prepare(
    "SELECT event_id, content_sha256 FROM event_log WHERE source_system = ? AND source_id = ? LIMIT 1"
  ).bind(event.source_system, event.source_id).first();

  if (!existing) throw new Error("duplicate_readback_failed");
  if ((existing.content_sha256 ?? null) !== (event.content_sha256 ?? null)) throw new Error("source_id_content_conflict");
  return { duplicate: true, event_id: existing.event_id };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "estate-event-ingress", schema: "event-ledger/1.0" });
    }
    if (request.method !== "POST" || url.pathname !== "/v1/events") return fail("not_found", 404);
    if (!env.INGEST_TOKEN || !env.EVENT_DB) return fail("ingress_not_configured", 503);

    const auth = request.headers.get("authorization") || "";
    if (!auth.startsWith("Bearer ") || !(await tokenMatches(auth.slice(7), env.INGEST_TOKEN))) {
      return fail("unauthorized", 401);
    }

    const length = Number(request.headers.get("content-length") || 0);
    if (length > MAX_BODY_BYTES) return fail("payload_too_large", 413);

    const text = await request.text();
    if (new TextEncoder().encode(text).byteLength > MAX_BODY_BYTES) return fail("payload_too_large", 413);

    let body;
    try { body = JSON.parse(text); } catch { return fail("invalid_json", 400); }

    try {
      const event = normalizeEvent(body);
      const result = await persistEvent(env.EVENT_DB, event);
      return json({ ok: true, ...result, processing_state: result.duplicate ? "existing" : "received" }, result.duplicate ? 200 : 201);
    } catch (error) {
      const message = String(error?.message || "");
      if (message === "source_id_content_conflict") return fail("source_id_content_conflict", 409);
      if (message === "duplicate_readback_failed") return fail("ingest_readback_failed", 503);
      if (/^invalid_|^payload_content_not_accepted$|^unknown_event_field$/.test(message)) return fail(message, 400);
      return fail("ingest_failed", 503);
    }
  }
};
