# Email records (kind `email`, ids EM-0001 …)

Each email in the case correspondence is a catalogue record of its own: one message, one catalogue id, one page at
`https://bucklerfamily.estate/catalogue/?id=EM-0001`. Added 10 November 2026 under core schema 0.4.0 (additive: new kind `email`,
new id prefix `EM`, new `email` block). No existing record is changed.

## Files
- `index.json` — metadata only, one row per record: id, timestamp, direction, correspondent(s), sender as shown, subject line, thread, whether
  the transcript is public, the part that holds the record, attachment count. Read-models (the ERP, the email archive) read this.
- `emails-01.json` … `emails-15.json` — the records (core schema), in date order, about 350 KB each.

## Counts (build of 2026-11-10)
- 1138 records, EM-0001 to EM-1138: 1056 from the email archive (with its redacted text) and
  82 from the case-mail index that the archive does not hold yet (metadata only, transcript "not yet transcribed").
- Transcripts public: 698. Held for editorial review: 369 (the archive copy is unchanged; the record still exists).
  Correspondents that are not a listed public body show as "an unlisted correspondent", with no personal name and no transcript, until confirmed.

## Dedupe (nothing is catalogued twice)
1. Same mailbox message id (`gm-…`) in more than one source: kept once.
2. Otherwise the same timestamp to the minute, sender and subject (normalised; "Re:"/"Fwd:" removed). Index rows carry no sender, so they
   match on the exact timestamp, correspondent and subject. Separate sends of one letter to different bodies stay separate records.
The second key is stored on each record as `email.dedupe_key`; ids are never reused.

## Rules
Additive only: a change to an existing EM record goes as a pull request labelled `catalogue-change`. Email addresses and contact numbers are
redacted; private individuals are not named; a transcript is held, not published, where it needs an editor's decision.

— Cedwyn editors
